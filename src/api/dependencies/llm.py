from __future__ import annotations

from langchain_openai import ChatOpenAI
from litestar.datastructures import State


def get_llm(state: State) -> ChatOpenAI:
    llm = getattr(state, "llm", None)
    if llm is None:
        raise RuntimeError("LLM client is not configured")

    return llm
