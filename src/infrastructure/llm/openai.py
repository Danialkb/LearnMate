from __future__ import annotations

import os

from langchain_openai import ChatOpenAI

from configs.env import Settings
from services.llm.enums import LLMUseCase


class LLMFactory:
    def __init__(self, settings: Settings):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")

        self.settings = settings
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

    def create(self, use_case: LLMUseCase) -> ChatOpenAI:
        base_config = {
            "model": self.settings.LLM_MODEL,
            "max_retries": 3,
            "timeout": 30,
        }

        match use_case:
            case LLMUseCase.SUMMARY:
                return ChatOpenAI(
                    **base_config,
                    temperature=0.2,
                    max_tokens=800,
                    frequency_penalty=0.3,
                    presence_penalty=0.0,
                )

            case LLMUseCase.QUIZ:
                return ChatOpenAI(
                    **base_config,
                    temperature=0.7,
                    max_tokens=500,
                    frequency_penalty=0.5,
                    presence_penalty=0.4,
                )

            case LLMUseCase.RAG:
                return ChatOpenAI(
                    **base_config,
                    temperature=0.1,
                    max_tokens=1000,
                    frequency_penalty=0.2,
                    presence_penalty=0.0,
                )

            case LLMUseCase.CHAT:
                return ChatOpenAI(
                    **base_config,
                    temperature=0.5,
                    max_tokens=1000,
                )
