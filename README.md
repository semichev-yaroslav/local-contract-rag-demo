# RAG по договорам на OpenAI

Локальный MVP для поиска ответов по договорам на русском языке. Приложение запускается локально, читает `DOCX`, извлекает метаданные, хранит структурированный слой в `SQLite/FTS5`, а semantic retrieval и генерацию ответа выполняет через OpenAI API.

## Что реализовано

- ingestion для `DOCX`
- извлечение метаданных правилами и эвристиками
- локальный реестр документов и чанков в `SQLite`
- exact/full-text поиск через `FTS5`
- semantic retrieval через `OpenAI vector stores`
- генерация ответа через `OpenAI Responses API`
- CLI и HTTP API

## Ограничения MVP

- поддерживается только `DOCX`
- OCR для сканов PDF не реализован
- признак подписи определяется вручную через overrides или упрощенным статусом `unknown`
- для semantic retrieval и генерации ответа нужен `OPENAI_API_KEY`

## Быстрый старт

1. Установить зависимости:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Подготовить переменные окружения:

```bash
export OPENAI_API_KEY="..."
export OPENAI_CHAT_MODEL="gpt-5-mini"
```

3. Положить документы в папку `data/raw`.

4. При необходимости описать ручные overrides в `data/manual_metadata.example.json` и сохранить как `data/manual_metadata.json`.

5. Выполнить индексацию:

```bash
python3 -m app.main ingest data/raw
```

6. Задать вопрос:

```bash
python3 -m app.main ask "какие условия постоплаты по договору с ООО Ромашка?"
```

7. Или запустить API:

```bash
uvicorn app.api:app --reload
```

## Настройки

- `OPENAI_API_KEY` обязателен для ingestion и semantic QA
- `OPENAI_BASE_URL` по умолчанию `https://api.openai.com/v1`
- `OPENAI_CHAT_MODEL` по умолчанию `gpt-5-mini`
- `OPENAI_VECTOR_STORE_NAME` по умолчанию `contract-knowledge-base`
- `OPENAI_VECTOR_STORE_ID` опционален, если нужен уже существующий vector store
- `DB_PATH` по умолчанию `data/db/contracts.sqlite3`
- `TOP_K` по умолчанию `6`

## Архитектура

1. Локальный сервис читает `DOCX` и извлекает metadata.
2. Metadata и локальные чанки сохраняются в `SQLite`.
3. Исходные файлы загружаются в `OpenAI vector store` с атрибутами документа.
4. На запросе сначала используется metadata/full-text слой, затем semantic retrieval через OpenAI.
5. Ответ синтезируется через `Responses API` по найденному контексту.

Подробности и пояснительная записка: [docs/explanatory_note.md](docs/explanatory_note.md)
