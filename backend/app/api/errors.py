"""Maps application errors to HTTP responses shaped as {"error", "detail"}."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors import AppError, InvalidInputError, NotFoundError, UpstreamError

logger = logging.getLogger(__name__)

_STATUS_BY_ERROR: dict[type[AppError], int] = {
    NotFoundError: 404,
    InvalidInputError: 422,
    UpstreamError: 502,
}


def _status_for(exc: AppError) -> int:
    return next(
        (status for error, status in _STATUS_BY_ERROR.items() if isinstance(exc, error)),
        500,
    )


def register_error_handlers(app: FastAPI) -> None:
    """Install the error handlers. Responses never include stack traces."""

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=_status_for(exc),
            content={"error": exc.code, "detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "detail": "Something went wrong."},
        )
