from dataclasses import dataclass
from typing import Protocol

from services.documents.retrieval import DocumentRetrievalService, RetrievedChunk


class TopicQuizChatModel(Protocol):
    async def ainvoke(self, input: str) -> object: ...


@dataclass(frozen=True, slots=True)
class TopicQuiz:
    answer: str
    sources: list[RetrievedChunk]
    used_general_knowledge: bool


class TopicQuizGenerator:
    def __init__(
        self,
        retrieval: DocumentRetrievalService,
    ):
        self.retrieval = retrieval
