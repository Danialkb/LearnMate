from __future__ import annotations

from langchain_openai import ChatOpenAI

from src.configs.env import Settings


def build_openai_llm(settings: Settings) -> ChatOpenAI:
    if settings.LLM_PROVIDER != "openai":
        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required for OpenAI LLM")

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.OPENAI_API_KEY,
    )
