## Project overview

This project is LearnMate, a local backend-only learning assistant.

The goal is to help the user learn LangChain, LangGraph, RAG, and LLM application architecture by building a useful personal app.

Main features:
- upload educational materials: videos, books, articles, documents
- generate summaries
- generate quizzes for knowledge retention
- support RAG-based question answering over uploaded materials


## Tech stack

- Python 3.12+
- Litestar for HTTP API
- Pydantic for validation and settings
- LangChain for LLM integration
- LangGraph for agent/workflow orchestration
- OpenAI via langchain-openai
- Qdrant for vector storage
- PostgreSQL for relational data if needed
- Docker / docker-compose for local infrastructure


## Architecture

This project uses a simplified layered architecture:

- api: HTTP layer (Litestar)
- services: business logic and application logic
- infrastructure: external integrations (LLM, DB, etc.)

There is no separate core/domain layer.
All business-level abstractions (like LLMUseCase) are located in services.


## LLM architecture

LLM provider-specific code belongs to:

src/infrastructure/llm/

Examples:
- OpenAI ChatOpenAI configuration
- LLMFactory implementation
- provider-specific clients

Use cases may include:
- SUMMARY
- QUIZ
- RAG
- CHAT

Do not create one global ChatOpenAI instance for all tasks if different configurations are needed.
Prefer an LLMFactory that creates clients by use case.

## Coding rules

- Prefer simple, readable code over over-engineering.
- Use type hints everywhere.
- Keep mypy clean.
- Avoid global side effects when possible.
- Do not set OPENAI_API_KEY through os.environ inside business code.
- Prefer passing api_key directly to ChatOpenAI.
- Keep provider-specific logic out of services.
- Do not put LangChain/OpenAI-specific details into core unless intentionally abstracted.


## Testing

When changing code:
- run mypy if available
- run ruff if available
- run tests if available
- do not ask the user before running tests, linters, format checks, type checks,
  or other non-mutating code analyzers

## Repository workflow

- Before committing, inspect the working tree and avoid reverting unrelated user changes.
- Keep commits focused, but include supporting tests or fixtures when they are part of the same behavior change.
- Prefer pushing to the current feature branch unless the user explicitly asks for a different branch.

## Other rules
Do not use src. in import statements
