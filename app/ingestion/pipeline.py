from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from app.ingestion.chunking import chunk_document
from app.ingestion.docx_reader import read_docx
from app.ingestion.metadata import extract_metadata
from app.openai_support.retrieval import OpenAIVectorStoreClient
from app.storage.sqlite_store import SQLiteStore


class IngestionService:
    def __init__(
        self,
        store: SQLiteStore,
        vector_store: OpenAIVectorStoreClient,
        manual_metadata_path: Path,
    ):
        self.store = store
        self.vector_store = vector_store
        self.manual_metadata_path = manual_metadata_path

    def ingest_path(self, path: Path, force: bool = False) -> Dict[str, object]:
        files = sorted(path.glob("*.docx")) if path.is_dir() else [path]
        overrides_map = self._load_overrides()
        indexed = 0
        skipped = 0
        failed = 0
        errors = []

        for file_path in files:
            try:
                raw_document = read_docx(file_path)
                existing_document = self.store.find_document_by_sha256(raw_document.sha256)
                if existing_document and not force:
                    skipped += 1
                    continue
                if existing_document and force:
                    self.vector_store.delete_document(existing_document)
                    self.store.delete_document_by_sha256(raw_document.sha256)

                overrides = overrides_map.get(file_path.name, {})
                document = extract_metadata(raw_document, overrides)
                chunks = chunk_document(document)
                document = self.vector_store.upload_document(file_path, document)
                self.store.upsert_document(document, chunks)
                indexed += 1
            except Exception as exc:
                failed += 1
                errors.append({"file": file_path.name, "error": str(exc)})

        return {"indexed": indexed, "skipped": skipped, "failed": failed, "errors": errors}

    def _load_overrides(self) -> Dict[str, Dict[str, object]]:
        if not self.manual_metadata_path.exists():
            return {}
        return json.loads(self.manual_metadata_path.read_text(encoding="utf-8"))
