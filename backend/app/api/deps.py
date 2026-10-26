"""Composition root: the only place that chooses adapters and wires dependencies."""

from collections.abc import AsyncIterator, Sequence
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from typing import Annotated

import httpx
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.auth import CurrentUser, SupabaseTokenVerifier
from app.application.agent.builder import AgentFeedBuilder
from app.application.agent.deps import AgentLimits
from app.application.agent.runners import AgentJournalLinker, AgentResolver
from app.application.ports import (
    AgentRunRepository,
    CatalogRepository,
    ChatModels,
    ExclusionRepository,
    FeedbackRepository,
    FeedRepository,
    JournalRepository,
    LanguageModel,
    MediaResolver,
    ProfileRepository,
    SongCatalog,
    SpeechToText,
    TasteGraph,
)
from app.application.rows.registry import default_registry
from app.application.services.ask import AskService
from app.application.services.background import AsyncioBackgroundRunner, BackgroundRunner
from app.application.services.demo import DemoSeedService
from app.application.services.exclusions import ExclusionService
from app.application.services.feed import FeedService
from app.application.services.feedback import FeedbackService
from app.application.services.items import ItemService
from app.application.services.journal import JournalService
from app.application.services.library import LibraryService
from app.application.services.profiles import ProfileService
from app.application.services.quiz import QuizService
from app.application.services.rate_limit import SlidingWindowRateLimiter
from app.application.services.resolve import ResolveService
from app.application.services.runs import AgentRunService
from app.application.services.taste import TasteService
from app.application.services.taste_match import TasteMatchService
from app.application.services.taste_profile import TasteProfileService
from app.core.errors import UnauthorizedError
from app.core.settings import Settings, get_settings
from app.domain.feed import ItemSource
from app.domain.models import DemoProfileSpec
from app.infrastructure.llm.factory import LLM_CALL_TIMEOUT_SECONDS, build_chat_model
from app.infrastructure.llm.language_model import LangChainLanguageModel
from app.infrastructure.llm.whisper import (
    GROQ_BASE_URL,
    WHISPER_TIMEOUT_SECONDS,
    GroqWhisperSpeechToText,
)
from app.infrastructure.media.cached import CachedMediaResolver
from app.infrastructure.media.youtube import (
    YOUTUBE_BASE_URL,
    YOUTUBE_TIMEOUT_SECONDS,
    YouTubeMediaResolver,
)
from app.infrastructure.music.itunes import (
    ITUNES_BASE_URL,
    ITUNES_TIMEOUT_SECONDS,
    ITunesSongCatalog,
)
from app.infrastructure.persistence.db import create_engine, create_sessionmaker
from app.infrastructure.persistence.memory_caches import InMemoryMediaCache, InMemoryQlooCache
from app.infrastructure.persistence.memory_feedback import (
    InMemoryExclusionRepository,
    InMemoryFeedbackRepository,
)
from app.infrastructure.persistence.memory_feeds import (
    InMemoryCatalogRepository,
    InMemoryFeedRepository,
)
from app.infrastructure.persistence.memory_journal import InMemoryJournalRepository
from app.infrastructure.persistence.memory_profiles import InMemoryProfileRepository
from app.infrastructure.persistence.memory_runs import InMemoryAgentRunRepository
from app.infrastructure.persistence.postgres_caches import PostgresMediaCache, PostgresQlooCache
from app.infrastructure.persistence.postgres_feedback import (
    PostgresExclusionRepository,
    PostgresFeedbackRepository,
)
from app.infrastructure.persistence.postgres_feeds import (
    PostgresCatalogRepository,
    PostgresFeedRepository,
)
from app.infrastructure.persistence.postgres_journal import PostgresJournalRepository
from app.infrastructure.persistence.postgres_profiles import PostgresProfileRepository
from app.infrastructure.persistence.postgres_runs import PostgresAgentRunRepository
from app.infrastructure.qloo.cached_taste_graph import CachedTasteGraph
from app.infrastructure.qloo.demo_profiles import load_demo_profiles
from app.infrastructure.qloo.http_taste_graph import QLOO_TIMEOUT_SECONDS, QlooHttpTasteGraph

SettingsDep = Annotated[Settings, Depends(get_settings)]


@dataclass(frozen=True)
class Adapters:
    """The adapters chosen for the ports. The LLM ones, speech and media are None when no key
    is set, and songs when the songs row is turned off. `journal_language_model` is the
    Groq-only model that may read journal text (rule 11)."""

    taste_graph: TasteGraph
    profiles: ProfileRepository
    feeds: FeedRepository
    catalog: CatalogRepository
    feedback: FeedbackRepository
    exclusions: ExclusionRepository
    runs: AgentRunRepository
    journal: JournalRepository
    media: MediaResolver | None = None
    language_model: LanguageModel | None = None
    chat_models: ChatModels | None = None
    songs: SongCatalog | None = None
    journal_language_model: LanguageModel | None = None
    speech: SpeechToText | None = None


def memory_adapters(
    taste_graph: TasteGraph,
    media: MediaResolver | None = None,
    songs: SongCatalog | None = None,
    journal_language_model: LanguageModel | None = None,
    speech: SpeechToText | None = None,
) -> Adapters:
    """In-memory storage around a taste graph: for tests and for local runs without a database."""
    return Adapters(
        taste_graph=taste_graph,
        profiles=InMemoryProfileRepository(),
        feeds=InMemoryFeedRepository(),
        catalog=InMemoryCatalogRepository(),
        feedback=InMemoryFeedbackRepository(),
        exclusions=InMemoryExclusionRepository(),
        runs=InMemoryAgentRunRepository(),
        journal=InMemoryJournalRepository(),
        media=media,
        songs=songs,
        journal_language_model=journal_language_model,
        speech=speech,
    )


@dataclass(frozen=True)
class Container:
    """Everything the routes need, built once when the app starts."""

    taste: TasteService
    profiles: ProfileService
    demo: DemoSeedService
    feeds: FeedService
    runs: AgentRunService
    feedback: FeedbackService
    items: ItemService
    library: LibraryService
    quiz: QuizService
    exclusions: ExclusionService
    journal: JournalService
    resolve: ResolveService
    taste_profile: TasteProfileService
    ask: AskService
    taste_match: TasteMatchService
    token_verifier: SupabaseTokenVerifier | None


def wire(
    adapters: Adapters,
    token_verifier: SupabaseTokenVerifier | None,
    demo_profiles: Sequence[DemoProfileSpec],
    settings: Settings,
    runner: BackgroundRunner,
) -> Container:
    """Build the services from chosen adapters. Tests call this with fakes."""
    taste = TasteService(adapters.taste_graph)
    profiles = ProfileService(adapters.profiles, adapters.journal)
    builder = AgentFeedBuilder(
        feedback=adapters.feedback,
        exclusions=adapters.exclusions,
        taste=adapters.taste_graph,
        runs=adapters.runs,
        rows=default_registry(settings.feed_row_size),
        limits=AgentLimits(
            max_tool_calls=settings.agent_max_tool_calls,
            max_model_calls=settings.agent_max_model_calls,
            timeout_seconds=settings.agent_timeout_seconds,
            max_retries=settings.agent_max_retries,
            feed_max_qloo_calls=settings.feed_max_qloo_calls,
            row_size=settings.feed_row_size,
        ),
        language_model=adapters.language_model,
        chat_models=adapters.chat_models,
        songs=adapters.songs,
        journal=adapters.journal,
    )
    rate_limiter = SlidingWindowRateLimiter(settings.feed_rate_limit_per_hour)
    feeds = FeedService(
        profiles,
        adapters.feeds,
        adapters.runs,
        adapters.exclusions,
        adapters.catalog,
        builder,
        runner,
        rate_limiter,
    )
    feedback = FeedbackService(
        profiles, adapters.feedback, adapters.exclusions, feeds, catalog=adapters.catalog
    )
    library = LibraryService(
        profiles, adapters.feedback, adapters.catalog, ItemSource(adapters.taste_graph.source)
    )
    journal = JournalService(
        profiles,
        adapters.journal,
        adapters.feedback,
        feedback,
        adapters.exclusions,
        feeds,
        adapters.runs,
        AgentJournalLinker(
            adapters.taste_graph,
            adapters.journal,
            adapters.runs,
            settings.link_max_searches,
            adapters.journal_language_model,
        ),
        runner,
        adapters.speech,
    )
    return Container(
        taste=taste,
        profiles=profiles,
        demo=DemoSeedService(
            adapters.profiles,
            taste,
            demo_profiles,
            adapters.feedback,
            adapters.exclusions,
            feeds,
            adapters.journal,
        ),
        feeds=feeds,
        runs=AgentRunService(profiles, adapters.runs),
        feedback=feedback,
        items=ItemService(
            profiles,
            adapters.feeds,
            adapters.catalog,
            adapters.exclusions,
            adapters.taste_graph,
            adapters.media,
            adapters.songs,
            adapters.journal,
        ),
        library=library,
        quiz=QuizService(
            profiles,
            adapters.exclusions,
            adapters.taste_graph,
            taste,
            feedback,
            settings.quiz_pairs,
        ),
        exclusions=ExclusionService(profiles, adapters.exclusions, feeds),
        journal=journal,
        resolve=ResolveService(
            profiles,
            adapters.exclusions,
            adapters.runs,
            AgentResolver(
                adapters.taste_graph,
                adapters.runs,
                settings.resolve_max_searches,
                adapters.language_model,
            ),
            runner,
        ),
        taste_profile=TasteProfileService(
            profiles,
            adapters.feedback,
            adapters.catalog,
            adapters.journal,
            library,
            adapters.taste_graph,
            settings.taste_map_max_nodes,
            adapters.language_model,
        ),
        ask=AskService(
            profiles,
            adapters.feeds,
            adapters.runs,
            adapters.exclusions,
            adapters.catalog,
            builder,
            runner,
            rate_limiter,
        ),
        taste_match=TasteMatchService(profiles, adapters.runs, adapters.catalog, builder),
        token_verifier=token_verifier,
    )


def build_llm(settings: Settings) -> tuple[ChatModels | None, LanguageModel | None]:
    """The main model and its fallback (Gemini, then Groq), when their settings are present."""
    primary_key = settings.llm_api_key.get_secret_value().strip()
    if not (settings.llm_provider.strip() and settings.llm_model.strip() and primary_key):
        return None, None
    primary = build_chat_model(settings.llm_provider, settings.llm_model, primary_key)
    fallback = None
    fallback_key = settings.llm_fallback_api_key.get_secret_value().strip()
    if (
        settings.llm_fallback_provider.strip()
        and settings.llm_fallback_model.strip()
        and fallback_key
    ):
        fallback = build_chat_model(
            settings.llm_fallback_provider, settings.llm_fallback_model, fallback_key
        )
    models = [model for model in (primary, fallback) if model is not None]
    return ChatModels(primary=primary, fallback=fallback), LangChainLanguageModel(models)


def groq_settings(settings: Settings) -> tuple[str, str] | None:
    """The Groq model and key, from whichever of the main or fallback LLM settings is Groq."""
    pairs = (
        (settings.llm_provider, settings.llm_model, settings.llm_api_key),
        (
            settings.llm_fallback_provider,
            settings.llm_fallback_model,
            settings.llm_fallback_api_key,
        ),
    )
    for provider, model, key in pairs:
        secret = key.get_secret_value().strip()
        if provider.strip().lower() == "groq" and model.strip() and secret:
            return model.strip(), secret
    return None


def build_journal_llm(settings: Settings) -> LanguageModel | None:
    """The Groq-only model that may read journal text: never a free Gemini key (rule 11)."""
    groq = groq_settings(settings)
    if groq is None:
        return None
    model, key = groq
    return LangChainLanguageModel(
        [build_chat_model("groq", model, key)], call_timeout=LLM_CALL_TIMEOUT_SECONDS
    )


@asynccontextmanager
async def build_container(settings: Settings) -> AsyncIterator[Container]:
    """Choose adapters from the settings, and close their connections on shutdown."""
    async with AsyncExitStack() as stack:
        qloo_key = settings.qloo_api_key.get_secret_value().strip()
        if not qloo_key:
            raise RuntimeError("QLOO_API_KEY is not set. MeloMind needs a Qloo key to run.")
        database_url = settings.database_url.get_secret_value().strip()
        if database_url:
            engine = create_engine(database_url)
            stack.push_async_callback(engine.dispose)
            db = create_sessionmaker(engine)
            profiles: ProfileRepository = PostgresProfileRepository(db)
            feeds: FeedRepository = PostgresFeedRepository(db)
            catalog: CatalogRepository = PostgresCatalogRepository(db)
            feedback: FeedbackRepository = PostgresFeedbackRepository(db)
            exclusions: ExclusionRepository = PostgresExclusionRepository(db)
            runs: AgentRunRepository = PostgresAgentRunRepository(db)
            journal: JournalRepository = PostgresJournalRepository(db)
            media_cache = PostgresMediaCache(db)
            qloo_cache = PostgresQlooCache(db)
        else:
            profiles = InMemoryProfileRepository()
            feeds = InMemoryFeedRepository()
            catalog = InMemoryCatalogRepository()
            feedback = InMemoryFeedbackRepository()
            exclusions = InMemoryExclusionRepository()
            runs = InMemoryAgentRunRepository()
            journal = InMemoryJournalRepository()
            media_cache = InMemoryMediaCache()
            qloo_cache = InMemoryQlooCache()

        qloo_client = await stack.enter_async_context(
            httpx.AsyncClient(base_url=settings.qloo_base_url, timeout=QLOO_TIMEOUT_SECONDS)
        )
        taste_graph: TasteGraph = CachedTasteGraph(
            QlooHttpTasteGraph(qloo_client, qloo_key), qloo_cache
        )

        youtube_key = settings.youtube_api_key.get_secret_value().strip()
        media: MediaResolver | None = None
        if youtube_key:
            youtube_client = await stack.enter_async_context(
                httpx.AsyncClient(base_url=YOUTUBE_BASE_URL, timeout=YOUTUBE_TIMEOUT_SECONDS)
            )
            media = CachedMediaResolver(
                YouTubeMediaResolver(youtube_client, youtube_key), media_cache
            )

        songs: SongCatalog | None = None
        if settings.songs_enabled:
            itunes_client = await stack.enter_async_context(
                httpx.AsyncClient(
                    base_url=ITUNES_BASE_URL,
                    timeout=ITUNES_TIMEOUT_SECONDS,
                    headers={"User-Agent": "MeloMind/0.1 (Qloo Agentic Hackathon)"},
                )
            )
            songs = ITunesSongCatalog(itunes_client)

        chat_models, language_model = build_llm(settings)
        speech: SpeechToText | None = None
        groq = groq_settings(settings)
        if groq is not None:
            groq_client = await stack.enter_async_context(
                httpx.AsyncClient(base_url=GROQ_BASE_URL, timeout=WHISPER_TIMEOUT_SECONDS)
            )
            speech = GroqWhisperSpeechToText(groq_client, groq[1], settings.stt_model)
        runner = AsyncioBackgroundRunner()
        stack.push_async_callback(runner.close)
        verifier = (
            SupabaseTokenVerifier.for_project(settings.supabase_url)
            if settings.supabase_url.strip()
            else None
        )
        adapters = Adapters(
            taste_graph=taste_graph,
            profiles=profiles,
            feeds=feeds,
            catalog=catalog,
            feedback=feedback,
            exclusions=exclusions,
            runs=runs,
            journal=journal,
            media=media,
            language_model=language_model,
            chat_models=chat_models,
            songs=songs,
            journal_language_model=build_journal_llm(settings),
            speech=speech,
        )
        yield wire(adapters, verifier, load_demo_profiles(), settings, runner)


def get_container(request: Request) -> Container:
    """The container the app built at startup."""
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]

_bearer = HTTPBearer(auto_error=False, description="Supabase access token")


async def get_current_user(
    container: ContainerDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    """The signed-in user, from `Authorization: Bearer <Supabase access token>`."""
    if credentials is None:
        raise UnauthorizedError("Sign in to continue.")
    if container.token_verifier is None:
        raise UnauthorizedError("Sign-in isn't set up on the server. Set SUPABASE_URL.")
    return await container.token_verifier.verify(credentials.credentials)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def get_taste_service(container: ContainerDep) -> TasteService:
    """Taste search."""
    return container.taste


def get_profile_service(container: ContainerDep) -> ProfileService:
    """Profiles and favourites."""
    return container.profiles


def get_demo_service(container: ContainerDep) -> DemoSeedService:
    """The demo seed."""
    return container.demo


def get_feed_service(container: ContainerDep) -> FeedService:
    """The feed: latest snapshot and refresh."""
    return container.feeds


def get_run_service(container: ContainerDep) -> AgentRunService:
    """Agent runs and their logs."""
    return container.runs


def get_feedback_service(container: ContainerDep) -> FeedbackService:
    """Likes, saves, opens and dismissals."""
    return container.feedback


def get_item_service(container: ContainerDep) -> ItemService:
    """Item details, more like this and previews."""
    return container.items


def get_library_service(container: ContainerDep) -> LibraryService:
    """Liked and saved items."""
    return container.library


def get_quiz_service(container: ContainerDep) -> QuizService:
    """The taste quiz."""
    return container.quiz


def get_exclusion_service(container: ContainerDep) -> ExclusionService:
    """The not-interested list."""
    return container.exclusions


def get_journal_service(container: ContainerDep) -> JournalService:
    """The journal."""
    return container.journal


def get_resolve_service(container: ContainerDep) -> ResolveService:
    """Resolving a typed favourite."""
    return container.resolve


def get_taste_profile_service(container: ContainerDep) -> TasteProfileService:
    """The taste page and map."""
    return container.taste_profile


def get_ask_service(container: ContainerDep) -> AskService:
    """Asking the agent for an extra row."""
    return container.ask


def get_taste_match_service(container: ContainerDep) -> TasteMatchService:
    """Taste match."""
    return container.taste_match


TasteServiceDep = Annotated[TasteService, Depends(get_taste_service)]
ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]
DemoServiceDep = Annotated[DemoSeedService, Depends(get_demo_service)]
FeedServiceDep = Annotated[FeedService, Depends(get_feed_service)]
RunServiceDep = Annotated[AgentRunService, Depends(get_run_service)]
FeedbackServiceDep = Annotated[FeedbackService, Depends(get_feedback_service)]
ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]
LibraryServiceDep = Annotated[LibraryService, Depends(get_library_service)]
QuizServiceDep = Annotated[QuizService, Depends(get_quiz_service)]
ExclusionServiceDep = Annotated[ExclusionService, Depends(get_exclusion_service)]
JournalServiceDep = Annotated[JournalService, Depends(get_journal_service)]
ResolveServiceDep = Annotated[ResolveService, Depends(get_resolve_service)]
TasteProfileServiceDep = Annotated[TasteProfileService, Depends(get_taste_profile_service)]
AskServiceDep = Annotated[AskService, Depends(get_ask_service)]
TasteMatchServiceDep = Annotated[TasteMatchService, Depends(get_taste_match_service)]
