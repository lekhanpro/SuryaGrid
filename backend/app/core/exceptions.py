"""Standard application exceptions."""

from datetime import UTC, datetime

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(
        self, status_code: int = 400, detail: str = "Bad request", error_code: str = "BAD_REQUEST"
    ):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code


class NotFoundError(AppException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail, error_code="NOT_FOUND")


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=401, detail=detail, error_code="UNAUTHORIZED")


class ForbiddenError(AppException):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=403, detail=detail, error_code="FORBIDDEN")


class RateLimitError(AppException):
    def __init__(self, detail: str = "Too many requests"):
        super().__init__(status_code=429, detail=detail, error_code="RATE_LIMITED")


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.detail,
            "details": None,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": exc.errors(),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
