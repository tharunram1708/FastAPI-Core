from fastapi import FastAPI

from app.api.router import router as api_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.middleware import register_middlewares
from app.db.session import init_db


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
        openapi_url=settings.OPENAPI_URL if settings.DOCS_ENABLED else None,
        docs_url=settings.DOCS_URL if settings.DOCS_ENABLED else None,
        redoc_url=settings.REDOC_URL if settings.DOCS_ENABLED else None,
        debug=settings.DEBUG,
    )

    app.state.settings = settings
    register_middlewares(app)
    register_exception_handlers(app)
    app.include_router(api_router)

    @app.on_event("startup")
    def create_database_tables() -> None:
        if settings.AUTO_CREATE_TABLES:
            init_db()

    return app


app = create_app()
