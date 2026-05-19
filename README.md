# LearnMate

Каркас учебного агента на `LangChain + LangGraph + Litestar`.

Задача проекта:
- принимать длинные конспекты, статьи или расшифровки видео;
- выделять ключевые тезисы;
- генерировать тестовые вопросы для закрепления материала;

## LangSmith tracing

Для локальной отладки LLM/RAG-пайплайнов можно включить LangSmith:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=learnmate-local
```

Трейсы размечаются по use case: `summary`, `topic-summary`, `rag`, `chat`
и `chat-agent`. В metadata попадают технические идентификаторы вроде
`document_id`, `source_count`, `limit` и `score_threshold`; полный контент
документов может попадать в prompt traces, поэтому для приватных материалов
включайте tracing осознанно.
