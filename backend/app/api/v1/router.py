"""Collects every v1 route under /api/v1."""

from fastapi import APIRouter

from app.api.v1.routes import demo, favourites, health, profiles, taste

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(demo.router)
api_router.include_router(profiles.router)
api_router.include_router(favourites.router)
api_router.include_router(taste.router)
