from __future__ import annotations

from dataclasses import dataclass

from langsmith import traceable

from services.documents.vector_index import DocumentVectorIndex, EmbeddingClient


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    text: str
    score: float
    document_id: str
    source_id: str | None
    chunk_index: int | None
    title: str | None
    page_start: int | None
    page_end: int | None


def _retrieval_inputs(inputs: dict[str, object]) -> dict[str, object]:
    return {
        "query": inputs.get("query"),
        "limit": inputs.get("limit"),
        "document_id": inputs.get("document_id"),
    }


def _retrieval_outputs(outputs: object) -> dict[str, object]:
    if not isinstance(outputs, list):
        return {"result_type": type(outputs).__name__}
    return {"chunk_count": len(outputs)}


class DocumentRetrievalService:
    def __init__(
        self,
        *,
        embeddings: EmbeddingClient,
        vector_index: DocumentVectorIndex,
    ) -> None:
        self._embeddings = embeddings
        self._vector_index = vector_index

    @traceable(
        name="RetrieveDocumentChunks",
        run_type="retriever",
        tags=["learnmate", "retrieval"],
        process_inputs=_retrieval_inputs,
        process_outputs=_retrieval_outputs,
    )
    async def retrieve(
        self,
        *,
        query: str,
        limit: int = 5,
        document_id: str | None = None,
    ) -> list[RetrievedChunk]:
        await self._vector_index.ensure_collection()
        query_vector = await self._embeddings.embed_query(query)
        results = await self._vector_index.search(
            query_vector=query_vector,
            limit=limit,
            document_id=document_id,
        )
        return [
            RetrievedChunk(
                text=self._string_payload(result.payload, "text") or "",
                score=result.score,
                document_id=self._string_payload(result.payload, "document_id") or "",
                source_id=self._string_payload(result.payload, "source_id"),
                chunk_index=self._int_payload(result.payload, "chunk_index"),
                title=self._string_payload(result.payload, "title"),
                page_start=self._int_payload(result.payload, "page_start"),
                page_end=self._int_payload(result.payload, "page_end"),
            )
            for result in results
        ]

    @staticmethod
    def _string_payload(payload: object, key: str) -> str | None:
        if not isinstance(payload, dict):
            return None
        value = payload.get(key)
        return value if isinstance(value, str) else None

    @staticmethod
    def _int_payload(payload: object, key: str) -> int | None:
        if not isinstance(payload, dict):
            return None
        value = payload.get(key)
        return value if isinstance(value, int) else None
