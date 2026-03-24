# Локальный RAG по договорам

Локальный MVP для поиска ответов по договорам на русском языке. Система поддерживает загрузку `DOCX`, извлекает метаданные, строит гибридный индекс (`SQLite/FTS5` + `Qdrant`) и использует локальную LLM через `Ollama` для ответов по содержанию документов.

## Что реализовано

- ingestion для `DOCX`
- извлечение метаданных правилами и эвристиками
- хранение реестра договоров и чанков в `SQLite`
- full-text поиск через `FTS5`
- векторный поиск в `Qdrant local`
- генерация ответа через `Ollama`
- CLI и HTTP API для индексации и запросов

## Ограничения MVP

- поддерживается только `DOCX`
- OCR для сканов PDF не реализован
- признак подписи определяется вручную через overrides или упрощенным статусом `unknown`
- извлечение метаданных основано на правилах; для нестандартных шаблонов потребуется доработка

## Быстрый старт

1. Установить зависимости:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Поднять локальные модели в `Ollama`:

```bash
ollama pull qwen2.5:7b
ollama pull qwen3-embedding:0.6b
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

Основные параметры читаются из переменных окружения:

- `OLLAMA_BASE_URL` по умолчанию `http://localhost:11434`
- `OLLAMA_CHAT_MODEL` по умолчанию `qwen2.5:7b`
- `OLLAMA_EMBED_MODEL` по умолчанию `qwen3-embedding:0.6b`
- `DB_PATH` по умолчанию `data/db/contracts.sqlite3`
- `QDRANT_PATH` по умолчанию `data/db/qdrant`
- `QDRANT_COLLECTION` по умолчанию `contract_chunks`
- `TOP_K` по умолчанию `6`

## Архитектура

Схема работы описана в [docs/explanatory_note.md](docs/explanatory_note.md).
