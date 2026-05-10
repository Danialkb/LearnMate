from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from services.documents.enums import DocumentLifecycleStatus, DocumentSummaryStyle
from services.documents.repositories import DocumentRepository, DocumentSummarySaveData

if TYPE_CHECKING:
    from infrastructure.db.models.document import DocumentChunk, DocumentSummary

logger = logging.getLogger(__name__)

PROMPT_VERSION = "summary-v1"
MAX_GROUP_CHARS = 12_000


class SummaryChatModel(Protocol):
    async def ainvoke(self, input: str) -> object: ...


class SummaryError(Exception):
    """Base summary service error."""


class DocumentNotFoundError(SummaryError): ...


class DocumentNotReadyError(SummaryError): ...


class DocumentHasNoChunksError(SummaryError): ...


class DocumentSummaryNotFoundError(SummaryError): ...


@dataclass(frozen=True, slots=True)
class GeneratedSummary:
    summary: DocumentSummary
    cached: bool


class DocumentSummaryService:
    def __init__(
        self,
        *,
        repository: DocumentRepository,
        llm: SummaryChatModel | None = None,
    ) -> None:
        self._repository = repository
        self._llm = llm

    async def get_summary(
        self,
        *,
        document_id: UUID,
        style: DocumentSummaryStyle,
    ) -> DocumentSummary:
        document = await self._repository.get_document_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError

        summary = await self._repository.get_summary(
            document_id=document.id,
            style=style,
            source_document_version=document.current_version,
        )
        if summary is None:
            raise DocumentSummaryNotFoundError
        return summary

    async def generate_summary(
        self,
        *,
        document_id: UUID,
        style: DocumentSummaryStyle,
        refresh: bool,
    ) -> GeneratedSummary:
        document = await self._repository.get_document_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError
        if document.lifecycle_status != DocumentLifecycleStatus.READY:
            raise DocumentNotReadyError

        cached_summary = await self._repository.get_summary(
            document_id=document.id,
            style=style,
            source_document_version=document.current_version,
        )
        if cached_summary is not None and not refresh:
            return GeneratedSummary(summary=cached_summary, cached=True)

        chunks = [chunk for chunk in document.chunks if chunk.content.strip()]
        if not chunks:
            raise DocumentHasNoChunksError
        if self._llm is None:
            raise RuntimeError("Summary LLM is not configured")

        content = await self._summarize_chunks(
            chunks=chunks,
            title=document.title,
            language=document.language,
            style=style,
        )
        summary = await self._repository.save_summary(
            DocumentSummarySaveData(
                document_id=document.id,
                style=style,
                language=document.language,
                content=content,
                prompt_version=PROMPT_VERSION,
                source_document_version=document.current_version,
            )
        )
        return GeneratedSummary(summary=summary, cached=False)

    async def _summarize_chunks(
        self,
        *,
        chunks: Sequence[DocumentChunk],
        title: str,
        language: str | None,
        style: DocumentSummaryStyle,
    ) -> str:
        if self._llm is None:
            raise RuntimeError("Summary LLM is not configured")

        groups = self._group_chunks(chunks)
        if len(groups) == 1:
            prompt = self._build_final_prompt(
                title=title,
                language=language,
                style=style,
                context=self._format_group(groups[0]),
            )
            return self._response_text(await self._llm.ainvoke(prompt))

        partial_summaries: list[str] = []
        for index, group in enumerate(groups, start=1):
            prompt = self._build_partial_prompt(
                title=title,
                language=language,
                style=style,
                group_index=index,
                group_count=len(groups),
                context=self._format_group(group),
            )
            partial_summaries.append(
                self._response_text(await self._llm.ainvoke(prompt))
            )

        final_context = "\n\n".join(
            f"Partial summary {index}:\n{summary}"
            for index, summary in enumerate(partial_summaries, start=1)
        )
        prompt = self._build_final_prompt(
            title=title,
            language=language,
            style=style,
            context=final_context,
        )
        return self._response_text(await self._llm.ainvoke(prompt))

    @staticmethod
    def _group_chunks(chunks: Sequence[DocumentChunk]) -> list[list[DocumentChunk]]:
        groups: list[list[DocumentChunk]] = []
        current_group: list[DocumentChunk] = []
        current_chars = 0

        for chunk in chunks:
            chunk_size = len(chunk.content)
            if current_group and current_chars + chunk_size > MAX_GROUP_CHARS:
                groups.append(current_group)
                current_group = []
                current_chars = 0

            current_group.append(chunk)
            current_chars += chunk_size

        if current_group:
            groups.append(current_group)
        return groups

    @staticmethod
    def _format_group(chunks: Sequence[DocumentChunk]) -> str:
        return "\n\n".join(
            f"[chunk {chunk.chunk_index}]\n{chunk.content.strip()}" for chunk in chunks
        )

    @classmethod
    def _build_partial_prompt(
        cls,
        *,
        title: str,
        language: str | None,
        style: DocumentSummaryStyle,
        group_index: int,
        group_count: int,
        context: str,
    ) -> str:
        language_instruction = cls._language_instruction(language)
        return (
            "You are LearnMate, a learning assistant. Summarize this part of an "
            "educational document so it can be combined with other partial "
            "summaries later.\n"
            f"Document title: {title}\n"
            f"Part: {group_index} of {group_count}\n"
            f"Output style: {cls._style_instruction(style)}\n"
            f"{language_instruction}\n"
            "Keep important concepts, definitions, steps, and examples. Do not "
            "invent information that is not in the context.\n\n"
            f"Context:\n{context}\n\n"
            "Partial summary:"
        )

    @classmethod
    def _build_final_prompt(
        cls,
        *,
        title: str,
        language: str | None,
        style: DocumentSummaryStyle,
        context: str,
    ) -> str:
        language_instruction = cls._language_instruction(language)
        return (
            "You are LearnMate, a learning assistant. Create a useful summary of "
            "the educational material using only the provided context.\n"
            f"Document title: {title}\n"
            f"Output style: {cls._style_instruction(style)}\n"
            f"{language_instruction}\n"
            "Focus on what the learner should understand and remember. Do not "
            "invent information that is not in the context.\n\n"
            f"Context:\n{context}\n\n"
            "Summary:"
        )

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
    def _language_instruction(language: str | None) -> str:
        if language:
            return f"Write the summary in this language: {language}."
        return "Write the summary in the main language of the context."

    @staticmethod
    def _response_text(response: object) -> str:
        content = getattr(response, "content", response)
        return str(content).strip()
