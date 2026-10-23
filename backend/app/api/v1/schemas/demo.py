"""Response schema for the demo seed."""

from uuid import UUID

from pydantic import BaseModel


class DemoSeedResponse(BaseModel):
    """The user's sample profiles."""

    profile_ids: list[UUID]
