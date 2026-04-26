from __future__ import annotations

from litestar import Router, post
from litestar.di import Provide

from api.dependencies.llm import get_llm_factory
from api.v1.schemas.chat import ChatRequest, ChatResponse
from infrastructure.llm.openai import LLMFactory
from infrastructure.logging import get_logger
from services.llm.enums import LLMUseCase

logger = get_logger(__name__)


@post("")
async def chat(data: ChatRequest, llm_factory: LLMFactory) -> ChatResponse:
    logger.info("Received chat request")
    llm = llm_factory.create(LLMUseCase.CHAT)
    response = await llm.ainvoke(data.message)
    logger.info("Chat response generated")
    return ChatResponse(answer=str(response.content))


chat_router = Router(
    path="/chat",
    dependencies={"llm_factory": Provide(get_llm_factory, sync_to_thread=False)},
    route_handlers=[chat],
    tags=["Chat"],
)
