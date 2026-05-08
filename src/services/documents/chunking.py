from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextBlock:
    text: str
    page_start: int | None = None
    page_end: int | None = None


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    chunk_index: int
    content: str
    token_count: int
    page_start: int | None = None
    page_end: int | None = None


class TextChunker:
    def __init__(self, *, chunk_size: int = 800, chunk_overlap: int = 120) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def split(self, blocks: list[TextBlock]) -> list[ChunkDraft]:
        chunks: list[ChunkDraft] = []
        for block in blocks:
            normalized = self._normalize_text(block.text)
            if not normalized:
                continue

            tokens = normalized.split()
            step = self._chunk_size - self._chunk_overlap

            for start in range(0, len(tokens), step):
                end = start + self._chunk_size
                token_slice = tokens[start:end]
                if not token_slice:
                    continue

                chunks.append(
                    ChunkDraft(
                        chunk_index=len(chunks),
                        content=" ".join(token_slice),
                        token_count=len(token_slice),
                        page_start=block.page_start,
                        page_end=block.page_end,
                    )
                )

                if end >= len(tokens):
                    break

        return chunks

    @staticmethod
    def _normalize_text(text: str) -> str:
        without_control_chars = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", " ", text)
        return re.sub(r"\s+", " ", without_control_chars).strip()
