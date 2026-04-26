from __future__ import annotations

from litestar.datastructures import State

from infrastructure.llm.openai import LLMFactory


def get_llm_factory(state: State) -> LLMFactory:
    llm_factory: LLMFactory | None = getattr(state, "llm_factory", None)

    if llm_factory is None:
        raise RuntimeError("LLM factory is not configured")

    return llm_factory
