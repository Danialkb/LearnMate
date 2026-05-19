# Architecture Decisions

## No separate core/domain layer

Decision:
Use only `api`, `services`, and `infrastructure` layers.

Reason:
The project is educational and should stay simple.

Implication:
Business abstractions, use cases, and service interfaces live in `services`.

## LLM provider code stays in infrastructure

Decision:
OpenAI and LangChain provider setup belongs in `src/infrastructure/llm/`.

Reason:
Services should describe what the app needs, not how a specific provider works.

Implication:
Use factories or small abstractions when services need LLM clients.
