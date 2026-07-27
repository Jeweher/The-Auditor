"""
File: app/core/exceptions.py
Folder: backend/app/core
Purpose: Domain-level exceptions and their mapping to HTTP responses.
         Business/service code raises these exceptions directly; it never
         builds an HTTPException itself. Keeps API layer free of business logic
         and keeps error responses consistent across the whole app.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for all domain/application exceptions."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "Resource not found."


class ValidationError(AppError):
    status_code = 422
    default_message = "Validation failed."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    default_message = "Resource conflict."


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_message = "Authentication required."


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    default_message = "You do not have permission to perform this action."


class ExternalServiceError(AppError):
    """Raised when a dependency (ChromaDB, LLM API, storage) fails."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_message = "An upstream service failed."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("AppError on %s %s: %s", request.method, request.url.path, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.__class__.__name__, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "InternalServerError", "message": "An unexpected error occurred."},
        )
