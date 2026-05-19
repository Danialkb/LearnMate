from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Protocol

from langchain_core.runnables import RunnableConfig
from langsmith import traceable

from services.documents.retrieval import DocumentRetrievalService, RetrievedChunk
from services.llm.tracing import llm_run_config

logger = logging.getLogger(__name__)

DEFAULT_SCORE_THRESHOLD = 0.25
MAX_SOURCE_TEXT_CHARS = 2_000


class RAGChatModel(Protocol):
    async def ainvoke(
        self,
        input: str,
        config: RunnableConfig | None = None,
    ) -> object: ...


@dataclass(frozen=True, slots=True)
class RAGAnswer:
    answer: str
    sources: list[RetrievedChunk]


def _rag_inputs(inputs: dict[str, object]) -> dict[str, object]:
    return {
        "question": inputs.get("question"),
        "limit": inputs.get("limit"),
        "document_id": inputs.get("document_id"),
        "score_threshold": inputs.get("score_threshold"),
    }


def _rag_outputs(outputs: object) -> dict[str, object]:
    sources = getattr(outputs, "sources", [])
    source_count = len(sources) if isinstance(sources, list) else None
    return {"source_count": source_count}


class RAGAnswerService:
    def __init__(
        self,
        *,
        retrieval: DocumentRetrievalService,
        llm: RAGChatModel,
    ) -> None:
        self._retrieval = retrieval
        self._llm = llm

    @traceable(
        name="RAGAnswer",
        run_type="chain",
        tags=["learnmate", "rag"],
        process_inputs=_rag_inputs,
        process_outputs=_rag_outputs,
    )
    async def answer(
        self,
        *,
        question: str,
        limit: int,
        document_id: str | None = None,
        score_threshold: float | None = None,
    ) -> RAGAnswer:
        chunks = await self._retrieval.retrieve(
            query=question,
            limit=limit,
            document_id=document_id,
        )
        sources = self._filter_sources(
            chunks,
            score_threshold=score_threshold,
        )
        if not sources:
            return RAGAnswer(
                answer=(
                    "I could not find relevant information in the uploaded materials."
                ),
                sources=[],
            )
        prompt = self._build_prompt(question=question, chunks=sources)
        logger.debug("Built RAG prompt with %s sources", len(sources))
        response = await self._llm.ainvoke(
            prompt,
            config=llm_run_config(
                run_name="RAGGenerateAnswer",
                tags=["rag"],
                metadata={
                    "document_id": document_id,
                    "source_count": len(sources),
                    "limit": limit,
                    "score_threshold": score_threshold,
                },
            ),
        )
        return RAGAnswer(answer=self._response_text(response), sources=sources)

    @classmethod
    def _filter_sources(
        cls,
        chunks: Sequence[RetrievedChunk],
        *,
        score_threshold: float | None,
    ) -> list[RetrievedChunk]:
        threshold = (
            DEFAULT_SCORE_THRESHOLD if score_threshold is None else score_threshold
        )
        return [
            replace(chunk, text=cls._trim_text(chunk.text.strip()))
            for chunk in chunks
            if chunk.text.strip() and chunk.score >= threshold
        ]

    @classmethod
    def _build_prompt(
        cls,
        *,
        question: str,
        chunks: Sequence[RetrievedChunk],
    ) -> str:
        context = "\n\n".join(
            cls._format_chunk(index=index, chunk=chunk)
            for index, chunk in enumerate(chunks, start=1)
        )
        return (
            "You are LearnMate, a learning assistant answering questions from "
            "uploaded educational materials.\n"
            "Use only the provided context. If the context does not contain the "
            "answer, say that the uploaded materials do not contain enough "
            "information.\n"
            "Answer in the same language as the user's question. Be concise and "
            "cite context chunks like [1] when useful.\n\n"
            f"Context:\n{context}\n\n"
            f"Question:\n{question}\n\n"
            "Answer:"
        )

    @classmethod
    def _format_chunk(cls, *, index: int, chunk: RetrievedChunk) -> str:
        page_range = cls._page_range(chunk)
        metadata = [
            f"title={chunk.title or 'Untitled'}",
            f"document_id={chunk.document_id}",
            f"source_id={chunk.source_id or 'unknown'}",
            f"chunk_index={chunk.chunk_index if chunk.chunk_index is not None else 'unknown'}",
        ]
        if page_range is not None:
            metadata.append(f"pages={page_range}")

        return f"[{index}] {'; '.join(metadata)}\n{chunk.text}"

    @staticmethod
    def _trim_text(text: str) -> str:
        if len(text) <= MAX_SOURCE_TEXT_CHARS:
            return text
        return f"{text[:MAX_SOURCE_TEXT_CHARS].rstrip()}..."

    @staticmethod
    def _page_range(chunk: RetrievedChunk) -> str | None:
        if chunk.page_start is None:
            return None
        if chunk.page_end is None or chunk.page_end == chunk.page_start:
            return str(chunk.page_start)
        return f"{chunk.page_start}-{chunk.page_end}"

    @staticmethod
    def _response_text(response: object) -> str:
        content = getattr(response, "content", response)
        return str(content)
