from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class VectorPoint:
    point_id: str
    vector: Sequence[float]
    payload: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class VectorSearchResult:
    point_id: str
    score: float
    payload: Mapping[str, object]


class EmbeddingClient(Protocol):
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class DocumentVectorIndex(Protocol):
    async def ensure_collection(self) -> None: ...

    async def upsert_points(self, points: Sequence[VectorPoint]) -> None: ...

    async def delete_document(self, document_id: str) -> None: ...

    async def search(
        self,
        *,
        query_vector: Sequence[float],
        limit: int,
        document_id: str | None = None,
    ) -> list[VectorSearchResult]: ...
