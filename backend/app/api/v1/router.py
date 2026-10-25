"""Collects every v1 route under /api/v1."""

from fastapi import APIRouter

from app.api.v1.routes import (
    agent_runs,
    demo,
    exclusions,
    favourites,
    feed,
    health,
    journal,
    profiles,
    taste,
    taste_profile,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(demo.router)
api_router.include_router(profiles.router)
api_router.include_router(favourites.router)
api_router.include_router(taste.router)
api_router.include_router(feed.router)
api_router.include_router(agent_runs.router)
api_router.include_router(exclusions.router)
api_router.include_router(journal.router)
api_router.include_router(taste_profile.router)
