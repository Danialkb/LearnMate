from __future__ import annotations

import os

from configs.env import Settings
from infrastructure.logging import get_logger

logger = get_logger(__name__)


def configure_langsmith(settings: Settings) -> None:
    """Expose LangSmith settings to LangChain's automatic tracer."""
    if not settings.LANGSMITH_TRACING:
        return

    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_PROJECT", settings.LANGSMITH_PROJECT)
    if settings.LANGSMITH_API_KEY:
        os.environ.setdefault("LANGSMITH_API_KEY", settings.LANGSMITH_API_KEY)
    if settings.LANGSMITH_ENDPOINT:
        os.environ.setdefault("LANGSMITH_ENDPOINT", settings.LANGSMITH_ENDPOINT)

    logger.info("LangSmith tracing enabled project=%s", settings.LANGSMITH_PROJECT)
