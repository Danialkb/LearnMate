from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from langchain_core.runnables import RunnableConfig


def llm_run_config(
    *,
    run_name: str,
    tags: Sequence[str],
    metadata: Mapping[str, object | None] | None = None,
) -> RunnableConfig:
    clean_metadata = {
        key: value for key, value in (metadata or {}).items() if value is not None
    }
    return cast(
        RunnableConfig,
        {
            "run_name": run_name,
            "tags": ["learnmate", *tags],
            "metadata": clean_metadata,
        },
    )
