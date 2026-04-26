from __future__ import annotations

from langchain_openai import ChatOpenAI
from litestar import Router, post

from api.v1.schemas.chat import ChatRequest, ChatResponse
from configs.logging import get_logger

logger = get_logger(__name__)


@post("")
async def chat(data: ChatRequest) -> ChatResponse:
    logger.info("Received chat request")
    llm = ChatOpenAI(model="gpt-4o-mini")
    response = await llm.ainvoke(data.message)
    logger.info("Chat response generated")
    return ChatResponse(answer=response.model_dump())


chat_router = Router(
    path="/chat",
    route_handlers=[chat],
)
