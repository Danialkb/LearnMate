from __future__ import annotations

from langchain_openai import ChatOpenAI

from configs.env import Settings
from services.llm.enums import LLMUseCase


class LLMFactory:
    def __init__(self, settings: Settings):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")

        self.settings = settings

    def create(self, use_case: LLMUseCase) -> ChatOpenAI:
        use_case_name = use_case.value.lower()
        base_config = {
            "model": self.settings.LLM_MODEL,
            "api_key": self.settings.OPENAI_API_KEY,
            "max_retries": 3,
            "timeout": 30,
            "tags": ["learnmate", use_case_name],
            "metadata": {
                "app": "learnmate",
                "use_case": use_case_name,
                "ls_model_name": f"{self.settings.LLM_MODEL}-{use_case_name}",
            },
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
