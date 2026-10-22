"""App factory. Run with `uvicorn app.main:app`."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.v1.router import api_router
from app.core.logging import configure_logging
from app.core.settings import APP_NAME, get_settings


def create_app() -> FastAPI:
    """Build the FastAPI app: logging, CORS for the frontend, error handlers and routes."""
    settings = get_settings()
    configure_logging()

    app = FastAPI(title=APP_NAME, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
