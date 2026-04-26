from litestar import Router

from api.v1.routes.chat import chat_router
from api.v1.routes.health import health_router

main_router = Router(
    path="/api/v1",
    route_handlers=[
        health_router,
        chat_router,
    ],
)
