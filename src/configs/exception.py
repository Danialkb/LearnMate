from litestar import Request, Response
import logging

from src.configs.request_context import get_request_id

logger = logging.getLogger(__name__)


def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    logger.exception(
        "Unhandled exception request_id=%s path=%s",
        get_request_id(),
        request.url.path,
    )

    return Response(
        content={
            "detail": "Internal server error",
            "request_id": get_request_id(),
        },
        status_code=500,
    )
