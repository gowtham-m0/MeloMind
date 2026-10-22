"""Health check route."""

from fastapi import APIRouter

from app.api.deps import QlooModeDep, SettingsDep
from app.api.v1.schemas.health import HealthResponse
from app.core.settings import APP_NAME

router = APIRouter(tags=["health"])


@router.get("/health")
async def get_health(settings: SettingsDep, qloo_mode: QlooModeDep) -> HealthResponse:
    """Report that the API is running, its environment, and its Qloo mode."""
    return HealthResponse(status="ok", app_name=APP_NAME, env=settings.app_env, qloo_mode=qloo_mode)
