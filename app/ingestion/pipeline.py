from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Protocol

from app.ingestion.chunking import chunk_document
from app.ingestion.docx_reader import read_docx
from app.ingestion.metadata import extract_metadata
from app.models import ContractDocument, DocumentChunk
from app.storage.sqlite_store import SQLiteStore
from app.storage.vector_store import QdrantVectorStore


class EmbedderProtocol(Protocol):
    def embed(self, texts: List[str]) -> List[List[float]]:
        ...


class IngestionService:
    def __init__(
        self,
        store: SQLiteStore,
        vector_store: QdrantVectorStore,
        embedder: EmbedderProtocol,
        manual_metadata_path: Path,
    ):
        self.store = store
        self.vector_store = vector_store
        self.embedder = embedder
        self.manual_metadata_path = manual_metadata_path

    def ingest_path(self, path: Path, force: bool = False) -> Dict[str, int]:
        files = sorted(path.glob("*.docx")) if path.is_dir() else [path]
        overrides_map = self._load_overrides()
        indexed = 0
        skipped = 0

        for file_path in files:
            raw_document = read_docx(file_path)
            already_exists = self.store.has_document(raw_document.sha256)
            if already_exists and not force:
                skipped += 1
                continue
            if already_exists and force:
                self.store.delete_document_by_sha256(raw_document.sha256)
            overrides = overrides_map.get(file_path.name, {})
            document = extract_metadata(raw_document, overrides)
            chunks = chunk_document(document)
            self.store.upsert_document(document, chunks)
            self._index_chunks(document, chunks)
            indexed += 1

        return {"indexed": indexed, "skipped": skipped}

    def _index_chunks(self, document: ContractDocument, chunks: List[DocumentChunk]) -> None:
        if not chunks:
            return
        vectors = self.embedder.embed([chunk.text for chunk in chunks])
        payloads = [
            {
                "doc_id": document.doc_id,
                "file_name": document.file_name,
                "section_name": chunk.section_name,
                "doc_type": document.doc_type,
                "counterparty": document.counterparty_normalized,
                "doc_number": document.doc_number,
                "doc_date": document.doc_date,
                "text": chunk.text,
            }
            for chunk in chunks
        ]
        self.vector_store.upsert(chunks, vectors, payloads)

    def _load_overrides(self) -> Dict[str, Dict[str, object]]:
        if not self.manual_metadata_path.exists():
            return {}
        return json.loads(self.manual_metadata_path.read_text(encoding="utf-8"))
