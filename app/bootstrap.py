from __future__ import annotations

from app.config import Settings
from app.ingestion.pipeline import IngestionService
from app.llm.embeddings import OllamaEmbeddingClient
from app.llm.generator import OllamaChatClient
from app.retrieval.service import QueryService
from app.storage.sqlite_store import SQLiteStore
from app.storage.vector_store import QdrantVectorStore


def build_runtime():
    settings = Settings.from_env()
    settings.ensure_dirs()
    store = SQLiteStore(settings.db_path)
    vector_store = QdrantVectorStore(settings.qdrant_path, settings.qdrant_collection)
    embedder = OllamaEmbeddingClient(settings.ollama_base_url, settings.embedding_model)
    generator = OllamaChatClient(settings.ollama_base_url, settings.chat_model)
    ingestion = IngestionService(
        store=store,
        vector_store=vector_store,
        embedder=embedder,
        manual_metadata_path=settings.manual_metadata_path,
    )
    query = QueryService(
        store=store,
        vector_store=vector_store,
        embedder=embedder,
        generator=generator,
        top_k=settings.top_k,
    )
    return {
        "settings": settings,
        "store": store,
        "vector_store": vector_store,
        "embedder": embedder,
        "generator": generator,
        "ingestion": ingestion,
        "query": query,
    }
