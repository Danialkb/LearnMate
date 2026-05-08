from __future__ import annotations

from collections.abc import Mapping, Sequence

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from configs.env import Settings
from services.documents.vector_index import VectorPoint, VectorSearchResult


class QdrantDocumentVectorIndex:
    def __init__(self, settings: Settings) -> None:
        self._client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=30,
        )
        self._collection_name = settings.QDRANT_COLLECTION_NAME
        self._vector_size = settings.OPENAI_EMBEDDING_DIMENSIONS
        self._distance = self._parse_distance(settings.QDRANT_DISTANCE)

    async def ensure_collection(self) -> None:
        if await self._client.collection_exists(self._collection_name):
            return

        await self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=models.VectorParams(
                size=self._vector_size,
                distance=self._distance,
            ),
        )

    async def upsert_points(self, points: Sequence[VectorPoint]) -> None:
        if not points:
            return

        await self._client.upsert(
            collection_name=self._collection_name,
            points=[
                models.PointStruct(
                    id=point.point_id,
                    vector=list(point.vector),
                    payload=dict(point.payload),
                )
                for point in points
            ],
            wait=True,
        )

    async def delete_document(self, document_id: str) -> None:
        await self._client.delete(
            collection_name=self._collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
            wait=True,
        )

    async def search(
        self,
        *,
        query_vector: Sequence[float],
        limit: int,
        document_id: str | None = None,
    ) -> list[VectorSearchResult]:
        response = await self._client.query_points(
            collection_name=self._collection_name,
            query=list(query_vector),
            query_filter=self._document_filter(document_id),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return [
            VectorSearchResult(
                point_id=str(point.id),
                score=point.score,
                payload=self._payload_to_mapping(point.payload),
            )
            for point in response.points
        ]

    @staticmethod
    def _parse_distance(value: str) -> models.Distance:
        normalized = value.upper()
        match normalized:
            case "COSINE":
                return models.Distance.COSINE
            case "DOT":
                return models.Distance.DOT
            case "EUCLID":
                return models.Distance.EUCLID
            case _:
                raise ValueError(f"Unsupported Qdrant distance: {value}")

    @staticmethod
    def _document_filter(document_id: str | None) -> models.Filter | None:
        if document_id is None:
            return None
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=document_id),
                )
            ]
        )

    @staticmethod
    def _payload_to_mapping(
        payload: Mapping[str, object] | None,
    ) -> Mapping[str, object]:
        if payload is None:
            return {}
        return payload
