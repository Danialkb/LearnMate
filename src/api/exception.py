import logging
from typing import Any

from litestar import Request, Response
from litestar.exceptions import HTTPException
from litestar.exceptions.responses import create_exception_response

from api.middlewares.request_context import get_request_id

logger = logging.getLogger(__name__)


def http_exception_handler(
    request: Request[Any, Any, Any],
    exc: HTTPException,
) -> Response[Any]:
    return create_exception_response(request=request, exc=exc)


def unhandled_exception_handler(
    request: Request[Any, Any, Any],
    exc: Exception,
) -> Response[dict[str, str]]:
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
