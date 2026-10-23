"""Composition root: the only place that chooses adapters and wires dependencies."""

from collections.abc import AsyncIterator, Sequence
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Literal

import httpx
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.auth import CurrentUser, SupabaseTokenVerifier
from app.application.agent.deps import AgentLimits
from app.application.agent.planner import AgentPlanner
from app.application.modes.registry import default_registry
from app.application.ports import (
    AgentRunRepository,
    ChatModels,
    ExclusionRepository,
    FeedbackRepository,
    LanguageModel,
    MediaResolver,
    ProfileRepository,
    SessionRepository,
    TasteGraph,
)
from app.application.services.background import AsyncioBackgroundRunner, BackgroundRunner
from app.application.services.demo import DemoSeedService
from app.application.services.exclusions import ExclusionService
from app.application.services.feedback import FeedbackService
from app.application.services.profiles import ProfileService
from app.application.services.rate_limit import SlidingWindowRateLimiter
from app.application.services.runs import AgentRunService
from app.application.services.sessions import SessionService
from app.application.services.shelf import ShelfService
from app.application.services.taste import TasteService
from app.application.services.warmup import WarmupService
from app.core.errors import UnauthorizedError
from app.core.settings import Settings, get_settings
from app.domain.models import DemoProfileSpec
from app.infrastructure.llm.factory import build_chat_model
from app.infrastructure.llm.language_model import LangChainLanguageModel
from app.infrastructure.media.cached import CachedMediaResolver
from app.infrastructure.media.demo import DemoMediaResolver
from app.infrastructure.media.youtube import (
    YOUTUBE_BASE_URL,
    YOUTUBE_TIMEOUT_SECONDS,
    YouTubeMediaResolver,
)
from app.infrastructure.persistence.db import create_engine, create_sessionmaker
from app.infrastructure.persistence.memory_caches import InMemoryMediaCache, InMemoryQlooCache
from app.infrastructure.persistence.memory_feedback import (
    InMemoryExclusionRepository,
    InMemoryFeedbackRepository,
)
from app.infrastructure.persistence.memory_profiles import InMemoryProfileRepository
from app.infrastructure.persistence.memory_runs import InMemoryAgentRunRepository
from app.infrastructure.persistence.memory_sessions import InMemorySessionRepository
from app.infrastructure.persistence.postgres_caches import PostgresMediaCache, PostgresQlooCache
from app.infrastructure.persistence.postgres_feedback import (
    PostgresExclusionRepository,
    PostgresFeedbackRepository,
)
from app.infrastructure.persistence.postgres_profiles import PostgresProfileRepository
from app.infrastructure.persistence.postgres_runs import PostgresAgentRunRepository
from app.infrastructure.persistence.postgres_sessions import PostgresSessionRepository
from app.infrastructure.qloo.cached_taste_graph import CachedTasteGraph
from app.infrastructure.qloo.demo_profiles import load_demo_profiles
from app.infrastructure.qloo.fixture_taste_graph import FixtureTasteGraph
from app.infrastructure.qloo.http_taste_graph import QLOO_TIMEOUT_SECONDS, QlooHttpTasteGraph

QlooMode = Literal["live", "demo_fixtures"]

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_qloo_mode(settings: SettingsDep) -> QlooMode:
    """Use live Qloo when an API key is set, and the hand-written demo fixtures otherwise."""
    return "live" if settings.qloo_api_key.get_secret_value().strip() else "demo_fixtures"


QlooModeDep = Annotated[QlooMode, Depends(get_qloo_mode)]


@dataclass(frozen=True)
class Adapters:
    """The adapters chosen for the ports. The LLM ones are None when no key is set."""

    taste_graph: TasteGraph
    media: MediaResolver
    profiles: ProfileRepository
    sessions: SessionRepository
    feedback: FeedbackRepository
    exclusions: ExclusionRepository
    runs: AgentRunRepository
    language_model: LanguageModel | None = None
    chat_models: ChatModels | None = None


def memory_adapters(taste_graph: TasteGraph, media: MediaResolver | None = None) -> Adapters:
    """In-memory storage around a taste graph: for tests and for local runs without a database."""
    return Adapters(
        taste_graph=taste_graph,
        media=media or DemoMediaResolver(),
        profiles=InMemoryProfileRepository(),
        sessions=InMemorySessionRepository(),
        feedback=InMemoryFeedbackRepository(),
        exclusions=InMemoryExclusionRepository(),
        runs=InMemoryAgentRunRepository(),
    )


@dataclass(frozen=True)
class Container:
    """Everything the routes need, built once when the app starts."""

    taste: TasteService
    profiles: ProfileService
    demo: DemoSeedService
    sessions: SessionService
    runs: AgentRunService
    feedback: FeedbackService
    shelf: ShelfService
    warmup: WarmupService
    exclusions: ExclusionService
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
    profiles = ProfileService(adapters.profiles)
    planner = AgentPlanner(
        feedback=adapters.feedback,
        exclusions=adapters.exclusions,
        taste=adapters.taste_graph,
        media=adapters.media,
        runs=adapters.runs,
        limits=AgentLimits(
            max_tool_calls=settings.agent_max_tool_calls,
            max_model_calls=settings.agent_max_model_calls,
            timeout_seconds=settings.agent_timeout_seconds,
            max_retries=settings.agent_max_retries,
        ),
        language_model=adapters.language_model,
        chat_models=adapters.chat_models,
    )
    sessions = SessionService(
        profiles,
        adapters.sessions,
        adapters.runs,
        adapters.exclusions,
        planner,
        runner,
        default_registry(),
        SlidingWindowRateLimiter(settings.plan_rate_limit_per_hour),
    )
    exclusions = ExclusionService(profiles, adapters.exclusions, adapters.sessions)
    shelf = ShelfService(profiles, adapters.sessions, adapters.exclusions, adapters.media)
    feedback = FeedbackService(
        profiles, sessions, adapters.sessions, adapters.feedback, exclusions, shelf
    )
    return Container(
        taste=taste,
        profiles=profiles,
        demo=DemoSeedService(adapters.profiles, taste, demo_profiles, sessions),
        sessions=sessions,
        runs=AgentRunService(profiles, adapters.runs),
        feedback=feedback,
        shelf=shelf,
        warmup=WarmupService(
            profiles,
            adapters.sessions,
            adapters.exclusions,
            taste,
            feedback,
            settings.warmup_pairs,
        ),
        exclusions=exclusions,
        token_verifier=token_verifier,
    )


def build_llm(settings: Settings) -> tuple[ChatModels | None, LanguageModel | None]:
    """Groq as the main model and Gemini as the fallback, when their settings are present."""
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


@asynccontextmanager
async def build_container(settings: Settings) -> AsyncIterator[Container]:
    """Choose adapters from the settings, and close their connections on shutdown."""
    async with AsyncExitStack() as stack:
        qloo_key = settings.qloo_api_key.get_secret_value().strip()
        database_url = settings.database_url.get_secret_value().strip()
        if database_url:
            engine = create_engine(database_url)
            stack.push_async_callback(engine.dispose)
            db = create_sessionmaker(engine)
            profiles: ProfileRepository = PostgresProfileRepository(db)
            sessions: SessionRepository = PostgresSessionRepository(db)
            feedback: FeedbackRepository = PostgresFeedbackRepository(db)
            exclusions: ExclusionRepository = PostgresExclusionRepository(db)
            runs: AgentRunRepository = PostgresAgentRunRepository(db)
            media_cache = PostgresMediaCache(db)
            qloo_cache = PostgresQlooCache(db)
        else:
            profiles = InMemoryProfileRepository()
            sessions = InMemorySessionRepository()
            feedback = InMemoryFeedbackRepository()
            exclusions = InMemoryExclusionRepository()
            runs = InMemoryAgentRunRepository()
            media_cache = InMemoryMediaCache()
            qloo_cache = InMemoryQlooCache()

        taste_graph: TasteGraph
        if qloo_key:
            qloo_client = await stack.enter_async_context(
                httpx.AsyncClient(base_url=settings.qloo_base_url, timeout=QLOO_TIMEOUT_SECONDS)
            )
            taste_graph = CachedTasteGraph(QlooHttpTasteGraph(qloo_client, qloo_key), qloo_cache)
        else:
            taste_graph = FixtureTasteGraph()

        youtube_key = settings.youtube_api_key.get_secret_value().strip()
        media: MediaResolver
        if youtube_key:
            youtube_client = await stack.enter_async_context(
                httpx.AsyncClient(base_url=YOUTUBE_BASE_URL, timeout=YOUTUBE_TIMEOUT_SECONDS)
            )
            media = CachedMediaResolver(
                YouTubeMediaResolver(youtube_client, youtube_key), media_cache
            )
        else:
            media = DemoMediaResolver()

        chat_models, language_model = build_llm(settings)
        runner = AsyncioBackgroundRunner()
        stack.push_async_callback(runner.close)
        verifier = (
            SupabaseTokenVerifier.for_project(settings.supabase_url)
            if settings.supabase_url.strip()
            else None
        )
        adapters = Adapters(
            taste_graph=taste_graph,
            media=media,
            profiles=profiles,
            sessions=sessions,
            feedback=feedback,
            exclusions=exclusions,
            runs=runs,
            language_model=language_model,
            chat_models=chat_models,
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


def get_session_service(container: ContainerDep) -> SessionService:
    """Sessions: planning, review and status changes."""
    return container.sessions


def get_run_service(container: ContainerDep) -> AgentRunService:
    """Agent runs and their logs."""
    return container.runs


def get_feedback_service(container: ContainerDep) -> FeedbackService:
    """Caregiver reactions and person signals."""
    return container.feedback


def get_shelf_service(container: ContainerDep) -> ShelfService:
    """The Person-mode shelf."""
    return container.shelf


def get_warmup_service(container: ContainerDep) -> WarmupService:
    """The Person-mode warm-up."""
    return container.warmup


def get_exclusion_service(container: ContainerDep) -> ExclusionService:
    """Rejected and hidden items."""
    return container.exclusions


TasteServiceDep = Annotated[TasteService, Depends(get_taste_service)]
ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]
DemoServiceDep = Annotated[DemoSeedService, Depends(get_demo_service)]
SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
RunServiceDep = Annotated[AgentRunService, Depends(get_run_service)]
FeedbackServiceDep = Annotated[FeedbackService, Depends(get_feedback_service)]
ShelfServiceDep = Annotated[ShelfService, Depends(get_shelf_service)]
WarmupServiceDep = Annotated[WarmupService, Depends(get_warmup_service)]
ExclusionServiceDep = Annotated[ExclusionService, Depends(get_exclusion_service)]
