import re
from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent
from langsmith import traceable

from services.documents.retrieval import RetrievedChunk
from services.documents.topic_summary import TopicSummaryService
from services.llm.agents.tools import (
    ChatAgentToolbox,
    ChatAgentToolContext,
    ChatAgentToolState,
)
from services.llm.rag import RAGAnswerService
from services.llm.tracing import llm_run_config


@dataclass(frozen=True, slots=True)
class ChatAgentAnswer:
    answer: str
    sources: list[RetrievedChunk]
    intent: str
    used_general_knowledge: bool


def _chat_agent_inputs(inputs: dict[str, object]) -> dict[str, object]:
    return {
        "message": inputs.get("message"),
        "limit": inputs.get("limit"),
        "document_id": inputs.get("document_id"),
        "score_threshold": inputs.get("score_threshold"),
    }


def _chat_agent_outputs(outputs: object) -> dict[str, object]:
    sources = getattr(outputs, "sources", [])
    source_count = len(sources) if isinstance(sources, list) else None
    return {
        "intent": getattr(outputs, "intent", None),
        "source_count": source_count,
        "used_general_knowledge": getattr(outputs, "used_general_knowledge", None),
    }


class ChatAgent:
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

    @traceable(
        name="ChatAgentAnswer",
        run_type="chain",
        tags=["learnmate", "chat-agent"],
        process_inputs=_chat_agent_inputs,
        process_outputs=_chat_agent_outputs,
    )
    async def answer(
        self,
        *,
        message: str,
        limit: int,
        document_id: str | None = None,
        score_threshold: float | None = None,
    ) -> ChatAgentAnswer:
        direct_route = self._direct_route(message)
        if direct_route == "rag":
            rag_answer = await self._rag.answer(
                question=message,
                limit=limit,
                document_id=document_id,
                score_threshold=score_threshold,
            )
            return ChatAgentAnswer(
                answer=rag_answer.answer,
                sources=rag_answer.sources,
                intent="rag",
                used_general_knowledge=False,
            )

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
                "Tool routing rules are strict:\n"
                "- Call summarize_uploaded_materials only when the user explicitly "
                "asks for a summary, recap, condensed version, тезисы, краткое "
                "содержание, резюме, конспект, or uses words like summary/"
                "summarize/recap/кратко/резюмируй/суммаризируй.\n"
                "- Do not call summarize_uploaded_materials for explain/tell me/"
                "describe/how does it work questions. Russian examples like "
                "'расскажи про ...', 'объясни ...', 'как работает ...', "
                "'что такое ...' must call answer_uploaded_materials.\n"
                "- Call answer_uploaded_materials for factual questions, "
                "explanations, definitions, process descriptions, and questions "
                "about how something works in uploaded materials.\n"
                "For summary style, infer brief, detailed, or bullets from the "
                "request. Default to brief.\n"
                "Answer in the user's language. Do not claim that uploaded "
                "sources were used unless a tool result used them."
            ),
        )
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config=llm_run_config(
                run_name="ChatAgentRouter",
                tags=["chat-agent"],
                metadata={
                    "document_id": document_id,
                    "limit": limit,
                    "score_threshold": score_threshold,
                },
            ),
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

    @classmethod
    def _direct_route(cls, message: str) -> str | None:
        normalized = message.strip().lower()
        if cls._is_summary_request(normalized):
            return None
        if cls._is_explanation_request(normalized):
            return "rag"
        return None

    @staticmethod
    def _is_summary_request(message: str) -> bool:
        return bool(
            re.search(
                r"\b(summary|summarize|recap)\b|"
                r"\b(резюме|резюмируй|суммаризируй|кратко|конспект|тезисы)\b",
                message,
            )
        )

    @staticmethod
    def _is_explanation_request(message: str) -> bool:
        return bool(
            re.match(
                r"^(расскажи|объясни|опиши|как работает|как устроен|"
                r"что такое|почему|зачем|tell me|explain|describe|"
                r"how does|how do|what is|why)\b",
                message,
            )
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
