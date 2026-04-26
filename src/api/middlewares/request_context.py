from __future__ import annotations

import logging
import time
from contextvars import ContextVar
from http import HTTPStatus
from typing import TYPE_CHECKING
from uuid import uuid4

from litestar import Request
from litestar.types import ASGIApp

if TYPE_CHECKING:
    from litestar.types import Receive, Scope, Send

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
logger = logging.getLogger(__name__)


def get_request_id() -> str:
    return request_id_var.get()


def _extract_request_id(request: Request) -> str:
    header_value = request.headers.get("x-request-id")
    if header_value:
        return header_value
    return uuid4().hex


def request_context_middleware(app: ASGIApp) -> ASGIApp:
    async def middleware(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await app(scope, receive, send)
            return

        request = Request(scope)
        request_id = _extract_request_id(request)
        token = request_id_var.set(request_id)
        started_at = time.perf_counter()
        response_status = HTTPStatus.INTERNAL_SERVER_ERROR

        async def send_wrapper(message: dict) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = HTTPStatus(message["status"])
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("utf-8")))
                message["headers"] = headers
            await send(message)

        try:
            logger.info(
                "Incoming request %s %s",
                request.method,
                request.url.path,
                extra={"request_id": request_id},
            )
            await app(scope, receive, send_wrapper)
        except Exception:
            logger.exception(
                "Unhandled error while processing %s %s",
                request.method,
                request.url.path,
                extra={"request_id": request_id},
            )
            raise
        finally:
            duration_ms = (time.perf_counter() - started_at) * 1000
            logger.info(
                "Completed request %s %s -> %s in %.2fms",
                request.method,
                request.url.path,
                response_status.value,
                duration_ms,
                extra={"request_id": request_id},
            )
            request_id_var.reset(token)

    return middleware
