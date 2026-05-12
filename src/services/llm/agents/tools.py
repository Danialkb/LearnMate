import functools
import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import ParamSpec, TypeVar

from langchain_core.tools import BaseTool, StructuredTool

from services.documents.enums import DocumentSummaryStyle
from services.documents.topic_summary import TopicSummary, TopicSummaryService
from services.llm.agents.helpers import parse_summary_style
from services.llm.rag import RAGAnswer, RAGAnswerService

logger = logging.getLogger(__name__)
P = ParamSpec("P")
R = TypeVar("R")


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


def log_tool_calling(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        func_args = inspect.signature(func).bind(*args, **kwargs)
        func_args.apply_defaults()

        params = {k: v for k, v in func_args.arguments.items() if k != "self"}
        func_name = getattr(func, "__name__", type(func).__name__)

        logger.info(f"--- TOOL START: {func_name} | Params: {params}")

        try:
            result = await func(*args, **kwargs)
            logger.info(f"--- TOOL SUCCESS: {func_name}")
            return result
        except Exception as e:
            logger.error(f"--- TOOL ERROR: {func_name} | Exception: {e}")
            raise

    return wrapper


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

    @log_tool_calling
    async def summarize_uploaded_materials(
        self,
        topic: str,
        style: str = DocumentSummaryStyle.BRIEF.value,
    ) -> str:
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

    @log_tool_calling
    async def answer_uploaded_materials(self, question: str) -> str:
        logging.info("TOOL called answer_uploaded_materials question=%s", question)
        self._state.rag = await self._rag.answer(
            question=question,
            limit=self._context.limit,
            document_id=self._context.document_id,
            score_threshold=self._context.score_threshold,
        )
        self._state.intent = "rag"
        return self._state.rag.answer
