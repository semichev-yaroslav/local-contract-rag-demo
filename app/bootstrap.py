from __future__ import annotations

from app.config import Settings
from app.ingestion.pipeline import IngestionService
from app.llm.generator import OpenAIChatClient
from app.openai_support.retrieval import OpenAIVectorStoreClient
from app.retrieval.service import QueryService
from app.storage.sqlite_store import SQLiteStore


def build_runtime():
    settings = Settings.from_env()
    settings.ensure_dirs()
    store = SQLiteStore(settings.db_path)
    vector_store = OpenAIVectorStoreClient(
        store=store,
        base_url=settings.openai_base_url,
        vector_store_name=settings.vector_store_name,
        configured_vector_store_id=settings.vector_store_id,
    )
    generator = OpenAIChatClient(settings.openai_base_url, settings.chat_model)
    ingestion = IngestionService(
        store=store,
        vector_store=vector_store,
        manual_metadata_path=settings.manual_metadata_path,
    )
    query = QueryService(
        store=store,
        vector_store=vector_store,
        generator=generator,
        top_k=settings.top_k,
    )
    return {
        "settings": settings,
        "store": store,
        "vector_store": vector_store,
        "generator": generator,
        "ingestion": ingestion,
        "query": query,
    }
