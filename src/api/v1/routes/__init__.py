from litestar import Router
from litestar.di import Provide

from api.dependencies.db import get_database_session
from api.v1.routes.chat import chat_router
from api.v1.routes.health import health_router
from api.v1.routes.materials import materials_router

main_router = Router(
    path="/api/v1",
    dependencies={"session": Provide(get_database_session)},
    route_handlers=[
        health_router,
        chat_router,
        materials_router,
    ],
)
