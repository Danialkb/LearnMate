# Coding Rules

General:
- prefer simple, readable code;
- use type hints everywhere;
- keep mypy clean;
- avoid global side effects;
- avoid over-engineering.

LLM code:
- do not create one global `ChatOpenAI` instance for all tasks;
- prefer an LLM factory that creates clients by use case;
- pass API keys directly to provider clients;
- do not set `OPENAI_API_KEY` through `os.environ` in business code;
- keep LangChain/OpenAI-specific details out of services unless intentionally abstracted.

Validation:
- run ruff, mypy, and tests when changing code if available;
- do not revert unrelated user changes.
