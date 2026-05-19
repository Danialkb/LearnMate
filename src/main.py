from __future__ import annotations

import uvicorn
from litestar import Litestar
from litestar.exceptions import HTTPException

from api.exception import http_exception_handler, unhandled_exception_handler
from api.middlewares.request_context import request_context_middleware
from api.v1.routes import main_router
from configs.env import Settings
from infrastructure.db.session import DatabaseService
from infrastructure.llm.langsmith import configure_langsmith
from infrastructure.llm.openai import LLMFactory
from infrastructure.logging import configure_logging, get_logger


def create_app() -> Litestar:
    settings = Settings()
    database_service = DatabaseService(settings)

    configure_logging(settings)
    configure_langsmith(settings)
    logger = get_logger(__name__)
    logger.info(
        "Starting %s in %s mode",
        settings.APP_NAME,
        "debug" if settings.DEBUG else "production",
    )

    app = Litestar(
        route_handlers=[main_router],
        debug=settings.DEBUG,
        middleware=[request_context_middleware],
        exception_handlers={
            HTTPException: http_exception_handler,
            Exception: unhandled_exception_handler,
        },
        request_max_body_size=settings.REQUEST_MAX_BODY_SIZE_BYTES,
        on_shutdown=[database_service.dispose],
    )
    app.state.settings = settings
    app.state.llm_factory = LLMFactory(settings)
    app.state.database_service = database_service
    return app


app = create_app()


def main() -> None:
    settings: Settings = app.state.settings
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
