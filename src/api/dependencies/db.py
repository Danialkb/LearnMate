from __future__ import annotations

from collections.abc import AsyncIterator

from litestar.datastructures import State
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.session import DatabaseService


def get_database_service(state: State) -> DatabaseService:
    database_service: DatabaseService | None = getattr(state, "database_service", None)

    if database_service is None:
        raise RuntimeError("Database service is not configured")

    return database_service


async def get_database_session(state: State) -> AsyncIterator[AsyncSession]:
    database_service = get_database_service(state)

    async with database_service.session() as session:
        yield session
