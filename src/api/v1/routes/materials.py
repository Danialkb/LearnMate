from litestar import Router

materials_router = Router(
    path="/materials",
    route_handlers=[],
    tags=["Materials"],
)
