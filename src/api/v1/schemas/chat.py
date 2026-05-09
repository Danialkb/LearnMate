from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    use_rag: bool = True
    document_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class RetrievedSource(BaseModel):
    text: str
    score: float
    document_id: str
    source_id: str | None = None
    chunk_index: int | None = None
    title: str | None = None
    page_start: int | None = None
    page_end: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[RetrievedSource] = Field(default_factory=list)
