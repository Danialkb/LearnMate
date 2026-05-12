from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Protocol

from services.documents.enums import DocumentSummaryStyle
from services.documents.retrieval import DocumentRetrievalService, RetrievedChunk
from services.llm.rag import DEFAULT_SCORE_THRESHOLD, MAX_SOURCE_TEXT_CHARS


class TopicSummaryChatModel(Protocol):
    async def ainvoke(self, input: str) -> object: ...


@dataclass(frozen=True, slots=True)
class TopicSummary:
    answer: str
    sources: list[RetrievedChunk]
    used_general_knowledge: bool


class TopicSummaryService:
    def __init__(
        self,
        *,
        retrieval: DocumentRetrievalService,
        llm: TopicSummaryChatModel,
    ) -> None:
        self._retrieval = retrieval
        self._llm = llm

    async def summarize(
        self,
        *,
        topic: str,
        style: DocumentSummaryStyle,
        limit: int,
        document_id: str | None = None,
        score_threshold: float | None = None,
    ) -> TopicSummary:
        chunks = await self._retrieval.retrieve(
            query=topic,
            limit=limit,
            document_id=document_id,
        )
        sources = self._filter_sources(chunks, score_threshold=score_threshold)
        if not sources:
            response = await self._llm.ainvoke(
                self._build_general_prompt(topic=topic, style=style)
            )
            return TopicSummary(
                answer=self._response_text(response),
                sources=[],
                used_general_knowledge=True,
            )

        response = await self._llm.ainvoke(
            self._build_grounded_prompt(topic=topic, style=style, chunks=sources)
        )
        return TopicSummary(
            answer=self._response_text(response),
            sources=sources,
            used_general_knowledge=False,
        )

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
    def _build_grounded_prompt(
        cls,
        *,
        topic: str,
        style: DocumentSummaryStyle,
        chunks: Sequence[RetrievedChunk],
    ) -> str:
        context = "\n\n".join(
            cls._format_chunk(index=index, chunk=chunk)
            for index, chunk in enumerate(chunks, start=1)
        )
        return (
            "You are LearnMate, a learning assistant. Summarize the requested "
            "topic using only the uploaded educational materials below.\n"
            f"Topic: {topic}\n"
            f"Output style: {cls._style_instruction(style)}\n"
            "Answer in the same language as the user's topic/request. Cite "
            "context chunks like [1] when useful. Do not invent information that "
            "is not in the context.\n\n"
            f"Context:\n{context}\n\n"
            "Summary:"
        )

    @classmethod
    def _build_general_prompt(cls, *, topic: str, style: DocumentSummaryStyle) -> str:
        return (
            "You are LearnMate, a learning assistant. The uploaded materials did "
            "not contain relevant information for this topic, so provide a "
            "general educational summary from your own knowledge.\n"
            f"Topic: {topic}\n"
            f"Output style: {cls._style_instruction(style)}\n"
            "Answer in the same language as the user's topic/request. Do not cite "
            "uploaded sources because none were used.\n\n"
            "Summary:"
        )

    @classmethod
    def _format_chunk(cls, *, index: int, chunk: RetrievedChunk) -> str:
        metadata = [
            f"title={chunk.title or 'Untitled'}",
            f"document_id={chunk.document_id}",
            f"source_id={chunk.source_id or 'unknown'}",
            f"chunk_index={chunk.chunk_index if chunk.chunk_index is not None else 'unknown'}",
        ]
        return f"[{index}] {'; '.join(metadata)}\n{chunk.text}"

    @staticmethod
    def _style_instruction(style: DocumentSummaryStyle) -> str:
        match style:
            case DocumentSummaryStyle.BRIEF:
                return "brief, 1-3 short paragraphs"
            case DocumentSummaryStyle.DETAILED:
                return "detailed, structured explanation with key sections"
            case DocumentSummaryStyle.BULLETS:
                return "bullet points with the most important ideas"
            case _:
                raise ValueError(f"Unsupported summary style: {style}")

    @staticmethod
    def _trim_text(text: str) -> str:
        if len(text) <= MAX_SOURCE_TEXT_CHARS:
            return text
        return f"{text[:MAX_SOURCE_TEXT_CHARS].rstrip()}..."

    @staticmethod
    def _response_text(response: object) -> str:
        content = getattr(response, "content", response)
        return str(content).strip()
