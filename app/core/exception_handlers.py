from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return _error_response(
        request=request,
        status_code=exc.status_code,
        detail=exc.detail,
        error_code=exc.error_code,
        headers=exc.headers,
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    return _error_response(
        request=request,
        status_code=exc.status_code,
        detail=str(exc.detail),
        error_code=_http_error_code(exc.status_code),
        headers=exc.headers,
    )


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return _error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Request validation failed",
        error_code="REQUEST_VALIDATION_ERROR",
        errors=exc.errors(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error",
        error_code="INTERNAL_SERVER_ERROR",
    )


def _error_response(
    *,
    request: Request,
    status_code: int,
    detail: str,
    error_code: str,
    errors: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    content: dict[str, Any] = {
        "detail": detail,
        "error_code": error_code,
    }
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        content["request_id"] = request_id

    if errors is not None:
        content["errors"] = errors

    response_headers = {"X-Error-Code": error_code}
    if request_id:
        response_headers["X-Request-ID"] = request_id
    if headers:
        response_headers.update(headers)

    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(content),
        headers=response_headers,
    )


def _http_error_code(status_code: int) -> str:
    return {
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    }.get(status_code, "HTTP_ERROR")
