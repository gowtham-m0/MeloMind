"""Composition root: the only place that chooses adapters and wires dependencies."""

from collections.abc import AsyncIterator, Sequence
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Literal

import httpx
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.auth import CurrentUser, SupabaseTokenVerifier
from app.application.ports import ProfileRepository, TasteGraph
from app.application.services.demo import DemoSeedService
from app.application.services.profiles import ProfileService
from app.application.services.taste import TasteService
from app.core.errors import UnauthorizedError
from app.core.settings import Settings, get_settings
from app.domain.models import DemoProfileSpec
from app.infrastructure.persistence.db import create_engine, create_sessionmaker
from app.infrastructure.persistence.memory_profiles import InMemoryProfileRepository
from app.infrastructure.persistence.postgres_profiles import PostgresProfileRepository
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
class Container:
    """Everything the routes need, built once when the app starts."""

    taste: TasteService
    profiles: ProfileService
    demo: DemoSeedService
    token_verifier: SupabaseTokenVerifier | None


def wire(
    taste_graph: TasteGraph,
    repository: ProfileRepository,
    token_verifier: SupabaseTokenVerifier | None,
    demo_profiles: Sequence[DemoProfileSpec],
) -> Container:
    """Build the services from chosen adapters. Tests call this with fakes."""
    taste = TasteService(taste_graph)
    return Container(
        taste=taste,
        profiles=ProfileService(repository),
        demo=DemoSeedService(repository, taste, demo_profiles),
        token_verifier=token_verifier,
    )


@asynccontextmanager
async def build_container(settings: Settings) -> AsyncIterator[Container]:
    """Choose adapters from the settings, and close their connections on shutdown."""
    async with AsyncExitStack() as stack:
        qloo_key = settings.qloo_api_key.get_secret_value().strip()
        taste_graph: TasteGraph
        if qloo_key:
            client = await stack.enter_async_context(
                httpx.AsyncClient(base_url=settings.qloo_base_url, timeout=QLOO_TIMEOUT_SECONDS)
            )
            taste_graph = QlooHttpTasteGraph(client, qloo_key)
        else:
            taste_graph = FixtureTasteGraph()

        database_url = settings.database_url.get_secret_value().strip()
        repository: ProfileRepository
        if database_url:
            engine = create_engine(database_url)
            stack.push_async_callback(engine.dispose)
            repository = PostgresProfileRepository(create_sessionmaker(engine))
        else:
            repository = InMemoryProfileRepository()

        verifier = (
            SupabaseTokenVerifier.for_project(settings.supabase_url)
            if settings.supabase_url.strip()
            else None
        )
        yield wire(taste_graph, repository, verifier, load_demo_profiles())


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


TasteServiceDep = Annotated[TasteService, Depends(get_taste_service)]
ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]
DemoServiceDep = Annotated[DemoSeedService, Depends(get_demo_service)]
