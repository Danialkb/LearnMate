from litestar import Router

materials_router = Router(
    path="/documents",
    route_handlers=[],
    tags=["Materials"],
)
