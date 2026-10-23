"""Base error types. The API layer maps each one to an HTTP status."""


class AppError(Exception):
    """An expected failure that should reach the client as a clean error response."""

    code = "app_error"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class UnauthorizedError(AppError):
    """The request has no valid sign-in token."""

    code = "unauthorized"


class NotFoundError(AppError):
    """The resource doesn't exist, or belongs to someone else."""

    code = "not_found"


class InvalidInputError(AppError):
    """The request is well-formed but breaks a rule."""

    code = "invalid_input"


class UpstreamError(AppError):
    """An external service (Qloo, YouTube or the LLM) failed or timed out."""

    code = "upstream_error"
