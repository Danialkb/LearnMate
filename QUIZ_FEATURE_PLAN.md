# План реализации фичи квизов

## Цель

Добавить в LearnMate генерацию квизов по загруженным учебным материалам, хранение правильных ответов и возможность принимать ответы пользователя на вопросы квиза.

Фича должна поддерживать базовый учебный сценарий:

1. Пользователь загружает материал.
2. Система генерирует квиз по материалу.
3. Пользователь получает вопросы без раскрытия правильных ответов.
4. Пользователь отправляет ответы.
5. Система проверяет ответы, возвращает результат, правильные ответы и объяснения.

## Основные требования

- Генерировать квизы только для документов со статусом `READY`.
- Использовать чанки документа как источник контекста.
- Не выдумывать вопросы вне содержимого документа.
- Хранить правильные ответы отдельно от пользовательского представления квиза.
- Возвращать правильные ответы только после отправки попытки или через отдельный служебный endpoint.
- Поддерживать повторную генерацию квиза через параметр `refresh`.
- Привязывать квиз к `document_id` и `source_document_version`, чтобы старые квизы не смешивались с новой версией документа.
- Использовать `LLMUseCase.QUIZ` через `LLMFactory`.
- Не добавлять LangChain/OpenAI-specific детали в API и бизнес-логику сверх минимального протокола `ainvoke`.

## Формат квиза

На первом этапе достаточно поддержать вопросы с одним правильным ответом.

Тип вопроса:

- `single_choice`

Структура одного вопроса:

```json
{
  "id": "q1",
  "question": "What is retrieval-augmented generation?",
  "options": [
    {
      "id": "a",
      "text": "A method that combines retrieval with generation"
    },
    {
      "id": "b",
      "text": "A database migration strategy"
    }
  ],
  "correct_option_id": "a",
  "explanation": "The material describes RAG as retrieving relevant context and passing it to the LLM before generation.",
  "source_chunk_indexes": [2, 3]
}
```

Публичный ответ API при выдаче квиза пользователю не должен включать:

- `correct_option_id`
- `explanation`, если пользователь еще не отвечал

## Модель данных

Добавить таблицу `document_quizzes`.

Поля:

- `id`: UUID
- `document_id`: UUID, FK на `documents.id`
- `title`: string, nullable
- `language`: string, nullable
- `question_count`: int
- `payload`: JSON
- `prompt_version`: string
- `source_document_version`: int
- `created_at`
- `updated_at`

`payload` хранит полный квиз, включая правильные ответы и объяснения.

Добавить уникальный индекс:

- `document_id`
- `source_document_version`

Если позже понадобятся разные типы квизов, уникальность можно расширить полями `difficulty`, `question_count`, `question_types`.

Добавить таблицу `quiz_attempts`.

Поля:

- `id`: UUID
- `quiz_id`: UUID, FK на `document_quizzes.id`
- `document_id`: UUID, FK на `documents.id`
- `answers`: JSON
- `score`: int
- `max_score`: int
- `result_payload`: JSON
- `created_at`

`answers` хранит ответы пользователя:

```json
[
  {
    "question_id": "q1",
    "selected_option_id": "a"
  }
]
```

`result_payload` хранит проверенные результаты:

```json
[
  {
    "question_id": "q1",
    "selected_option_id": "a",
    "correct_option_id": "a",
    "is_correct": true,
    "explanation": "..."
  }
]
```

## Сервисный слой

Создать `services/documents/quiz.py`.

Основные классы и ошибки:

- `DocumentQuizService`
- `GeneratedQuiz`
- `QuizNotFoundError`
- `QuizAttemptNotFoundError`
- `DocumentNotFoundError`
- `DocumentNotReadyError`
- `DocumentHasNoChunksError`

Основные методы:

```python
async def generate_quiz(
    self,
    *,
    document_id: UUID,
    question_count: int,
    refresh: bool,
) -> GeneratedQuiz: ...

async def get_quiz(
    self,
    *,
    document_id: UUID,
) -> DocumentQuiz: ...

async def submit_attempt(
    self,
    *,
    quiz_id: UUID,
    answers: Sequence[QuizAnswerInput],
) -> QuizAttemptResult: ...
```

Ответственность сервиса:

- Проверить существование документа.
- Проверить `DocumentLifecycleStatus.READY`.
- Получить чанки документа.
- Сгруппировать чанки по лимиту символов или токенов.
- Построить prompt для генерации квиза.
- Вызвать LLM через протокол `QuizChatModel`.
- Распарсить JSON-ответ модели.
- Провалидировать структуру квиза через Pydantic-модели.
- Сохранить квиз через репозиторий.
- При отправке попытки сравнить ответы пользователя с `correct_option_id`.
- Вернуть пользователю score, правильные ответы и объяснения.

## Prompt для генерации

Версия prompt:

```python
PROMPT_VERSION = "quiz-v1"
```

Требования к prompt:

- Просить модель вернуть только валидный JSON.
- Указать количество вопросов.
- Указать язык ответа: язык документа, если известен.
- Запретить вопросы вне предоставленного контекста.
- Для каждого вопроса требовать:
  - уникальный `id`
  - текст вопроса
  - 4 варианта ответа
  - ровно один `correct_option_id`
  - краткое объяснение
  - список `source_chunk_indexes`

Пример инструкции:

```text
Create a quiz from the provided educational material.
Use only the context below.
Return only valid JSON matching the schema.
Each question must have exactly four options and one correct answer.
Include a short explanation for why the correct answer is correct.
Do not include facts that are not supported by the context.
```

## Репозиторий

Расширить `services/documents/repositories.py`.

Добавить dataclass:

- `DocumentQuizSaveData`
- `QuizAttemptCreateData`

Добавить методы в `DocumentRepository`:

```python
async def get_quiz(
    self,
    *,
    document_id: UUID,
    source_document_version: int,
) -> DocumentQuiz | None: ...

async def save_quiz(self, data: DocumentQuizSaveData) -> DocumentQuiz: ...

async def get_quiz_by_id(self, quiz_id: UUID) -> DocumentQuiz | None: ...

async def create_quiz_attempt(
    self,
    data: QuizAttemptCreateData,
) -> QuizAttempt: ...
```

Реализовать методы в `infrastructure/db/repositories/documents.py`.

## API

Расширить `api/v1/schemas/documents.py`.

Добавить схемы:

- `DocumentQuizGenerateRequest`
- `DocumentQuizQuestionOptionResponse`
- `DocumentQuizQuestionResponse`
- `DocumentQuizResponse`
- `QuizAnswerRequestItem`
- `QuizAttemptSubmitRequest`
- `QuizAttemptQuestionResultResponse`
- `QuizAttemptResponse`

Endpoint генерации:

```text
POST /v1/documents/{document_id}/quiz
```

Request:

```json
{
  "question_count": 10,
  "refresh": false
}
```

Response:

```json
{
  "quiz_id": "...",
  "document_id": "...",
  "question_count": 10,
  "questions": [
    {
      "id": "q1",
      "question": "...",
      "options": [
        {
          "id": "a",
          "text": "..."
        }
      ]
    }
  ],
  "cached": false,
  "created_at": "..."
}
```

Endpoint получения текущего квиза:

```text
GET /v1/documents/{document_id}/quiz
```

Возвращает квиз без правильных ответов.

Endpoint отправки ответов:

```text
POST /v1/documents/{document_id}/quiz/{quiz_id}/attempts
```

Request:

```json
{
  "answers": [
    {
      "question_id": "q1",
      "selected_option_id": "a"
    }
  ]
}
```

Response:

```json
{
  "attempt_id": "...",
  "quiz_id": "...",
  "score": 7,
  "max_score": 10,
  "results": [
    {
      "question_id": "q1",
      "selected_option_id": "a",
      "correct_option_id": "a",
      "is_correct": true,
      "explanation": "..."
    }
  ]
}
```

## Валидация

Правила request validation:

- `question_count`: от 1 до 20.
- `answers`: не пустой список.
- каждый `question_id` должен существовать в квизе.
- каждый `selected_option_id` должен существовать среди options вопроса.
- дубликаты `question_id` в одной попытке запрещены.

Правила LLM response validation:

- JSON должен парситься без fallback на произвольный текст.
- количество вопросов должно соответствовать `question_count` или быть явно ограничено допустимым диапазоном.
- у каждого вопроса должно быть минимум 2 и максимум 6 options, но prompt просит 4.
- `correct_option_id` должен ссылаться на существующий option.
- `source_chunk_indexes` должны ссылаться на реальные чанки.
- пустые вопросы, варианты и объяснения запрещены.

## Безопасность правильных ответов

Правильные ответы хранятся в БД, но не возвращаются в публичном response квиза.

Разделить внутренние и внешние представления:

- internal model: содержит `correct_option_id` и `explanation`
- response schema: скрывает `correct_option_id` до отправки attempt

Не передавать `payload` напрямую наружу.

## Тесты

Unit tests для `DocumentQuizService`:

- документ не найден -> `DocumentNotFoundError`
- документ не `READY` -> `DocumentNotReadyError`
- документ без чанков -> `DocumentHasNoChunksError`
- существующий квиз возвращается из кеша при `refresh=False`
- новый квиз создается при `refresh=True`
- невалидный JSON от LLM приводит к контролируемой ошибке
- `submit_attempt` корректно считает score
- `submit_attempt` возвращает правильные ответы и объяснения
- неизвестный `question_id` отклоняется
- неизвестный `selected_option_id` отклоняется

API tests:

- `POST /documents/{id}/quiz` не раскрывает правильные ответы.
- `GET /documents/{id}/quiz` не раскрывает правильные ответы.
- `POST /documents/{id}/quiz/{quiz_id}/attempts` возвращает score и правильные ответы.
- HTTP-коды:
  - `404` для отсутствующего документа или квиза
  - `409` для неготового документа
  - `400` для документа без чанков или невалидных ответов

Repository tests:

- сохранение квиза
- получение квиза по `document_id` и `source_document_version`
- сохранение попытки
- уникальность квиза для версии документа

## Миграции

Добавить Alembic migration:

1. Создать `document_quizzes`.
2. Создать `quiz_attempts`.
3. Добавить FK и индексы.
4. Добавить unique constraint для актуального кеша квиза.

Проверить downgrade:

- удалить `quiz_attempts`
- удалить `document_quizzes`

## Этапы реализации

### Этап 1. Контракты и модели

- Добавить SQLAlchemy-модели `DocumentQuiz` и `QuizAttempt`.
- Добавить relationships в `Document`.
- Добавить Alembic migration.
- Добавить dataclass-контракты репозитория.
- Реализовать методы репозитория.

### Этап 2. Генерация квиза

- Добавить `DocumentQuizService`.
- Добавить Pydantic-модели внутреннего payload.
- Реализовать prompt `quiz-v1`.
- Реализовать JSON parsing и validation.
- Сохранять квиз в БД.
- Добавить кеширование по `document_id` и `source_document_version`.

### Этап 3. API генерации и чтения

- Добавить request/response schemas.
- Добавить `POST /documents/{document_id}/quiz`.
- Добавить `GET /documents/{document_id}/quiz`.
- Подключить маршруты в `materials_router`.
- Убедиться, что правильные ответы не уходят в response квиза.

### Этап 4. Ответы пользователя

- Добавить `submit_attempt` в сервис.
- Проверять ответы пользователя по сохраненному payload.
- Сохранять попытку в `quiz_attempts`.
- Возвращать score, правильные ответы и объяснения.
- Добавить `POST /documents/{document_id}/quiz/{quiz_id}/attempts`.

### Этап 5. Тесты и проверки

- Покрыть сервис unit-тестами.
- Покрыть API smoke/integration тестами.
- Покрыть репозиторий тестами, если в проекте уже есть инфраструктура для DB tests.
- Запустить:
  - `ruff`
  - `mypy`
  - `pytest`

## Минимальный MVP

Для первой рабочей версии достаточно:

- один квиз на текущую версию документа
- только `single_choice` вопросы
- 4 варианта ответа
- один правильный ответ
- объяснение после отправки попытки
- score без истории нескольких пользователей

Историю попыток уже можно хранить в `quiz_attempts`, но без отдельной user-модели.

## Возможные улучшения после MVP

- уровни сложности: `easy`, `medium`, `hard`
- несколько типов вопросов: `true_false`, `open_text`, `multiple_choice`
- генерация квиза по выбранной теме или главе
- RAG-проверка открытых ответов
- spaced repetition
- статистика слабых тем
- повторная попытка с новыми вопросами
- экспорт квиза в Markdown или JSON
- режим тренировки без сохранения attempt
