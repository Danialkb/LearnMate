from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_openai import OpenAIEmbeddings

from configs.env import Settings


class OpenAIEmbeddingClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")

        embedding_kwargs: dict[str, Any] = {
            "model": settings.OPENAI_EMBEDDING_MODEL,
            "dimensions": settings.OPENAI_EMBEDDING_DIMENSIONS,
            "api_key": settings.OPENAI_API_KEY,
            "max_retries": 3,
            "timeout": 30,
        }
        self._embeddings = OpenAIEmbeddings(**embedding_kwargs)

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = await self._embeddings.aembed_documents(list(texts))
        return [list(vector) for vector in vectors]

    async def embed_query(self, text: str) -> list[float]:
        vector = await self._embeddings.aembed_query(text)
        return list(vector)
