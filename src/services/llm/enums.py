from enum import StrEnum


class LLMUseCase(StrEnum):
    SUMMARY = "SUMMARY"
    QUIZ = "QUIZ"
    RAG = "RAG"
    CHAT = "CHAT"
