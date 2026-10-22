"""Response schema for the health check."""

from typing import Literal

from pydantic import BaseModel

from app.api.deps import QlooMode


class HealthResponse(BaseModel):
    """The API is up, which environment it runs in, and where recommendations come from."""

    status: Literal["ok"]
    app_name: str
    env: str
    qloo_mode: QlooMode
