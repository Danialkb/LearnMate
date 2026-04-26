from __future__ import annotations

from langchain_openai import ChatOpenAI
from litestar import Router, post
from litestar.di import Provide

from src.api.dependencies.llm import get_llm
from src.api.v1.schemas.chat import ChatRequest, ChatResponse
from src.configs.logging import get_logger

logger = get_logger(__name__)


@post("")
async def chat(data: ChatRequest, llm: ChatOpenAI) -> ChatResponse:
    logger.info("Received chat request")
    response = await llm.ainvoke(data.message)
    logger.info("Chat response generated")
    return ChatResponse(answer=response.model_dump())


chat_router = Router(
    path="/chat",
    dependencies={"llm": Provide(get_llm)},
    route_handlers=[chat],
)
