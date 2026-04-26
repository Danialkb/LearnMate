from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler
from rich.text import Text

from src.configs.env import Settings
from src.configs.request_context import get_request_id


class RequestAwareRichHandler(RichHandler):
    def render_message(self, record: logging.LogRecord, message: str):
        message_text = super().render_message(record, message)
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


def _build_handlers(settings: Settings) -> tuple[logging.Handler, logging.Handler]:
    console_handler = RequestAwareRichHandler(
        rich_tracebacks=True,
        show_path=False,
        show_time=True,
        show_level=True,
        markup=True,
    )
    console_handler.setLevel(settings.LOG_LEVEL)
    console_handler.addFilter(ContextFilter())

    log_file = Path(settings.LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(settings.LOG_LEVEL)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | "
            "request_id=%(request_id)s | %(message)s"
        )
    )
    file_handler.addFilter(ContextFilter())
    return console_handler, file_handler


def configure_logging(settings: Settings) -> None:
    console_handler, file_handler = _build_handlers(settings)

    logging.basicConfig(
        level=settings.LOG_LEVEL,
        handlers=[console_handler, file_handler],
        force=True,
    )

    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("litestar").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
