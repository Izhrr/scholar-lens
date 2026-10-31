from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Domain error that maps to an HTTP status with a user-safe message."""

    status_code = 400

    def __init__(self, detail: str, **extra: object) -> None:
        super().__init__(detail)
        self.detail = detail
        self.extra = extra


class BadRequestError(AppError):
    status_code = 400


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class PayloadTooLargeError(AppError):
    status_code = 413


class UnprocessableError(AppError):
    status_code = 422


class DependencyUnavailableError(AppError):
    status_code = 503


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, **exc.extra})
