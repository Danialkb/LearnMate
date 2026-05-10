# Summary Logic

LearnMate stores generated document summaries in Postgres and reuses them until
the caller explicitly requests a refresh.

The primary user-facing summary UX is chat-driven: a user can ask
`/api/v1/chat` for a summary by topic, for example "сделай summary по Redis".
The chat agent searches uploaded materials first and falls back to a general
educational summary when no relevant uploaded chunks are found.

## Flow

1. A document is uploaded and indexed into ordered `DocumentChunk` rows.
2. `POST /api/v1/documents/{document_id}/summary` checks whether a summary
   already exists for the document version and requested style.
3. If a cached summary exists and `refresh=false`, LearnMate returns it without
   calling the LLM.
4. If no cached summary exists, or `refresh=true`, LearnMate summarizes the
   document chunks with `LLMUseCase.SUMMARY` and saves the result.
5. `GET /api/v1/documents/{document_id}/summary?style=brief` reads a saved
   summary without generating a new one.

## Chat Topic Summary Flow

1. `POST /api/v1/chat` receives a natural language request.
2. `ChatAgentService` creates a LangChain agent with tools.
3. For summary requests, the agent calls `summarize_uploaded_materials`.
4. `TopicSummaryService` retrieves relevant chunks by topic.
5. If chunks are found, the summary is grounded in uploaded materials and
   returns sources.
6. If no chunks are found, LearnMate returns a general summary with no sources.

## Storage

Summaries are stored in `document_summaries`.

Important fields:

- `document_id`: source document.
- `style`: `brief`, `detailed`, or `bullets`.
- `content`: generated summary text.
- `prompt_version`: prompt contract used to generate the content.
- `source_document_version`: document version the summary belongs to.

The unique key is `document_id + style + source_document_version`.

## Service Rules

- Summary is generated from `DocumentChunk.content`, ordered by `chunk_index`.
- A document must be `READY`.
- A document must have at least one non-empty chunk.
- Topic summaries from chat are not persisted because they depend on a query and
  retrieval result set.
- Provider-specific LLM setup stays in `infrastructure/llm`.
- Business logic stays in `services/documents/summary.py`.
- Long documents use a simple map-reduce flow: partial summaries per chunk group,
  then a final summary over the partial summaries.
