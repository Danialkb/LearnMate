from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent
from langchain_core.tools import BaseTool, StructuredTool

from services.documents.enums import DocumentSummaryStyle
from services.documents.retrieval import RetrievedChunk
from services.documents.topic_summary import TopicSummary, TopicSummaryService
from services.llm.rag import RAGAnswer, RAGAnswerService


@dataclass(frozen=True, slots=True)
class ChatAgentAnswer:
    answer: str
    sources: list[RetrievedChunk]
    intent: str
    used_general_knowledge: bool


@dataclass(frozen=True, slots=True)
class ChatAgentToolContext:
    limit: int
    document_id: str | None
    score_threshold: float | None


@dataclass(slots=True)
class ChatAgentToolState:
    summary: TopicSummary | None = None
    rag: RAGAnswer | None = None
    intent: str = "chat"


class ChatAgentToolbox:
    def __init__(
        self,
        *,
        rag: RAGAnswerService,
        topic_summary: TopicSummaryService,
        context: ChatAgentToolContext,
        state: ChatAgentToolState,
    ) -> None:
        self._rag = rag
        self._topic_summary = topic_summary
        self._context = context
        self._state = state

    def tools(self) -> list[BaseTool]:
        return [
            StructuredTool.from_function(
                coroutine=self.summarize_uploaded_materials,
                name="summarize_uploaded_materials",
                description=(
                    "Summarize a topic from uploaded materials, with a general "
                    "knowledge fallback when no relevant uploaded materials exist."
                ),
            ),
            StructuredTool.from_function(
                coroutine=self.answer_uploaded_materials,
                name="answer_uploaded_materials",
                description="Answer a question using uploaded materials.",
            ),
        ]

    async def summarize_uploaded_materials(
        self,
        topic: str,
        style: str = DocumentSummaryStyle.BRIEF.value,
    ) -> str:
        logging.info(f"TOOL called summarize_uploaded_materials topic: {topic} {style}")
        summary_style = parse_summary_style(style)
        self._state.summary = await self._topic_summary.summarize(
            topic=topic,
            style=summary_style,
            limit=self._context.limit,
            document_id=self._context.document_id,
            score_threshold=self._context.score_threshold,
        )
        self._state.intent = "summary"
        return self._state.summary.answer

    async def answer_uploaded_materials(self, question: str) -> str:
        logging.info(f"TOOL called summarize_uploaded_materials topic: {question}")
        self._state.rag = await self._rag.answer(
            question=question,
            limit=self._context.limit,
            document_id=self._context.document_id,
            score_threshold=self._context.score_threshold,
        )
        self._state.intent = "rag"
        return self._state.rag.answer


class ChatAgentService:
    def __init__(
        self,
        *,
        model: Any,
        rag: RAGAnswerService,
        topic_summary: TopicSummaryService,
    ) -> None:
        self._model = model
        self._rag = rag
        self._topic_summary = topic_summary

    async def answer(
        self,
        *,
        message: str,
        limit: int,
        document_id: str | None = None,
        score_threshold: float | None = None,
    ) -> ChatAgentAnswer:
        tool_state = ChatAgentToolState()
        toolbox = ChatAgentToolbox(
            rag=self._rag,
            topic_summary=self._topic_summary,
            context=ChatAgentToolContext(
                limit=limit,
                document_id=document_id,
                score_threshold=score_threshold,
            ),
            state=tool_state,
        )

        agent = create_agent(
            model=self._model,
            tools=toolbox.tools(),
            system_prompt=(
                "You are LearnMate, a learning assistant for uploaded educational "
                "materials.\n"
                "If the user asks to summarize, make a summary, produce a recap, "
                "or uses Russian/Kazakh equivalents like 'сделай summary', "
                "'кратко', 'резюме', call summarize_uploaded_materials.\n"
                "If the user asks a factual question about uploaded materials, "
                "call answer_uploaded_materials.\n"
                "For summary style, infer brief, detailed, or bullets from the "
                "request. Default to brief.\n"
                "Answer in the user's language. Do not claim that uploaded "
                "sources were used unless a tool result used them."
            ),
        )
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]}
        )
        answer = self._last_message_text(result)

        if tool_state.summary is not None:
            return ChatAgentAnswer(
                answer=tool_state.summary.answer,
                sources=tool_state.summary.sources,
                intent=tool_state.intent,
                used_general_knowledge=tool_state.summary.used_general_knowledge,
            )
        if tool_state.rag is not None:
            return ChatAgentAnswer(
                answer=tool_state.rag.answer,
                sources=tool_state.rag.sources,
                intent=tool_state.intent,
                used_general_knowledge=False,
            )
        return ChatAgentAnswer(
            answer=answer,
            sources=[],
            intent=tool_state.intent,
            used_general_knowledge=True,
        )

    @staticmethod
    def _last_message_text(result: object) -> str:
        if not isinstance(result, dict):
            return str(result)

        messages = result.get("messages")
        if not isinstance(messages, list) or not messages:
            return ""

        content = getattr(messages[-1], "content", messages[-1])
        if isinstance(content, str):
            return content
        return str(content)


def parse_summary_style(style: str) -> DocumentSummaryStyle:
    normalized = style.strip().lower()
    for summary_style in DocumentSummaryStyle:
        if normalized in {summary_style.value, summary_style.name.lower()}:
            return summary_style
    return DocumentSummaryStyle.BRIEF
