from __future__ import annotations

import uvicorn
from litestar import Litestar

from api.middlewares.request_context import request_context_middleware
from api.v1.routes import main_router
from configs.env import Settings
from api.exception import unhandled_exception_handler
from infrastructure.logging import configure_logging, get_logger
from infrastructure.llm.openai import build_openai_llm


def create_app() -> Litestar:
    settings = Settings()

    configure_logging(settings)
    logger = get_logger(__name__)
    logger.info("Starting %s in %s mode", settings.APP_NAME, "debug" if settings.DEBUG else "production")

    app = Litestar(
        route_handlers=[main_router],
        debug=settings.DEBUG,
        middleware=[request_context_middleware],
        exception_handlers={
            Exception: unhandled_exception_handler,
        },
    )
    app.state.settings = settings
    app.state.llm = (
        build_openai_llm(settings)
        if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY
        else None
    )
    return app


app = create_app()


def main() -> None:
    settings: Settings = app.state.settings
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_config=None,
    )


if __name__ == "__main__":
    main()
