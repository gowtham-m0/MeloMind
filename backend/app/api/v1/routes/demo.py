"""Demo seed route: the sample profiles behind "Try the demo"."""

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, DemoServiceDep
from app.api.v1.schemas.demo import DemoSeedResponse

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/seed")
async def seed_demo(user: CurrentUserDep, demo: DemoServiceDep) -> DemoSeedResponse:
    """Create the sample profiles for this user, once. Calling it again changes nothing."""
    return DemoSeedResponse(profile_ids=await demo.seed(user.id))
