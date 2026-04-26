from __future__ import annotations

import logging
from typing import cast

from rich.logging import RichHandler
from rich.text import Text

from api.middlewares.request_context import get_request_id
from configs.env import Settings


class RequestAwareRichHandler(RichHandler):  # type: ignore[misc]
    def render_message(self, record: logging.LogRecord, message: str) -> Text:
        message_text = cast(Text, super().render_message(record, message))
        request_id = getattr(record, "request_id", get_request_id())
        if request_id and request_id != "-":
            return Text(f"[{request_id}] ", style="bold cyan") + message_text
        return message_text


class ContextFilter(logging.Filter):
    """Inject shared contextual fields into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        request_id = getattr(record, "request_id", None)
        if not request_id or request_id == "-":
            record.request_id = get_request_id()
        return True


def _build_handlers(settings: Settings) -> logging.Handler:
    console_handler = RequestAwareRichHandler(
        rich_tracebacks=True,
        show_path=False,
        show_time=True,
        show_level=True,
        markup=True,
    )
    console_handler.setLevel(settings.LOG_LEVEL)
    console_handler.addFilter(ContextFilter())
    return console_handler


def configure_logging(settings: Settings) -> None:
    console_handler = _build_handlers(settings)

    logging.basicConfig(
        level=settings.LOG_LEVEL,
        handlers=[console_handler],
        force=True,
    )

    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("litestar").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
