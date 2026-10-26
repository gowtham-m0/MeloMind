"""Response schema for the health check."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """The API is up, and which environment it runs in."""

    status: Literal["ok"]
    app_name: str
    env: str
