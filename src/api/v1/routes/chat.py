from __future__ import annotations

from litestar import Router, post
from litestar.di import Provide

from api.dependencies.documents import get_document_vector_index, get_embedding_client
from api.dependencies.llm import get_llm_factory
from api.v1.schemas.chat import ChatRequest, ChatResponse, RetrievedSource
from infrastructure.llm.embeddings import OpenAIEmbeddingClient
from infrastructure.llm.openai import LLMFactory
from infrastructure.logging import get_logger
from infrastructure.vector import QdrantDocumentVectorIndex
from services.documents.retrieval import DocumentRetrievalService, RetrievedChunk
from services.llm.enums import LLMUseCase
from services.llm.rag import RAGAnswerService

logger = get_logger(__name__)


@post("")
async def chat(
    data: ChatRequest,
    llm_factory: LLMFactory,
    embedding_client: OpenAIEmbeddingClient,
    document_vector_index: QdrantDocumentVectorIndex,
) -> ChatResponse:
    logger.info("Received chat request")
    if data.use_rag:
        retrieval = DocumentRetrievalService(
            embeddings=embedding_client,
            vector_index=document_vector_index,
        )
        service = RAGAnswerService(
            retrieval=retrieval,
            llm=llm_factory.create(LLMUseCase.RAG),
        )
        result = await service.answer(
            question=data.message,
            limit=data.top_k,
            document_id=data.document_id,
            score_threshold=data.score_threshold,
        )
        logger.info("RAG chat response generated sources=%s", len(result.sources))
        return ChatResponse(
            answer=result.answer,
            sources=[_source_from_chunk(chunk) for chunk in result.sources],
        )

    llm = llm_factory.create(LLMUseCase.CHAT)
    response = await llm.ainvoke(data.message)
    logger.info("Chat response generated")
    return ChatResponse(answer=str(response.content))


def _source_from_chunk(chunk: RetrievedChunk) -> RetrievedSource:
    return RetrievedSource(
        text=chunk.text,
        score=chunk.score,
        document_id=chunk.document_id,
        source_id=chunk.source_id,
        chunk_index=chunk.chunk_index,
        title=chunk.title,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
    )


chat_router = Router(
    path="/chat",
    dependencies={
        "llm_factory": Provide(get_llm_factory, sync_to_thread=False),
        "embedding_client": Provide(get_embedding_client, sync_to_thread=False),
        "document_vector_index": Provide(
            get_document_vector_index,
            sync_to_thread=False,
        ),
    },
    route_handlers=[chat],
    tags=["Chat"],
)
