# Architecture

LearnMate uses a simplified layered architecture.

Layers:
- `api`: Litestar HTTP routes, dependencies, request/response schemas;
- `services`: business logic, use cases, orchestration;
- `infrastructure`: external integrations such as OpenAI, Qdrant, PostgreSQL, S3.

Rules:
- there is no separate `core` or `domain` layer;
- business-level abstractions belong in `services`;
- provider-specific LLM code belongs in `src/infrastructure/llm/`;
- services should not depend on OpenAI-specific implementation details;
- do not use `src.` in import statements.
