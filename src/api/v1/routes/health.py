from litestar import get, Router


@get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


health_router = Router(
    path="",
    route_handlers=[health],
)
