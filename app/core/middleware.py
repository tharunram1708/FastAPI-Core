import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from app.core.config import settings


REQUEST_ID_HEADER = "X-Request-ID"
PROCESS_TIME_HEADER = "X-Process-Time-ms"

logger = logging.getLogger("app.requests")


def register_middlewares(app: FastAPI) -> None:
    configure_logging()
    app.middleware("http")(request_context_middleware)


def configure_logging() -> None:
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def request_context_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
    request.state.request_id = request_id

    start_time = perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        logger.exception(
            "request_failed request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )
        raise
    finally:
        process_time_ms = (perf_counter() - start_time) * 1000

        if "response" in locals():
            response.headers[REQUEST_ID_HEADER] = request_id
            response.headers[PROCESS_TIME_HEADER] = f"{process_time_ms:.2f}"

        logger.info(
            "request_completed request_id=%s method=%s path=%s status_code=%s duration_ms=%.2f client=%s",
            request_id,
            request.method,
            request.url.path,
            status_code,
            process_time_ms,
            request.client.host if request.client else "-",
        )
