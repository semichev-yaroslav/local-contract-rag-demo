from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI

from app.models import ContractDocument, RetrievedChunk
from app.storage.sqlite_store import SQLiteStore


class OpenAIVectorStoreClient:
    def __init__(
        self,
        store: SQLiteStore,
        base_url: str,
        vector_store_name: str,
        configured_vector_store_id: str = "",
    ):
        self.store = store
        self.base_url = base_url
        self.vector_store_name = vector_store_name
        self.configured_vector_store_id = configured_vector_store_id
        self._client: Optional[OpenAI] = None

    def upload_document(self, path: Path, document: ContractDocument) -> ContractDocument:
        client = self._get_client()
        vector_store_id = self.ensure_vector_store_id()
        with path.open("rb") as file_handle:
            file_object = client.files.create(file=file_handle, purpose="assistants")
        vector_store_file = client.vector_stores.files.create_and_poll(
            vector_store_id=vector_store_id,
            file_id=file_object.id,
            attributes=self._build_attributes(document),
        )
        document.openai_file_id = file_object.id
        document.openai_vector_store_file_id = vector_store_file.id
        return document

    def delete_document(self, document: ContractDocument) -> None:
        client = self._get_client()
        vector_store_id = self.get_vector_store_id()
        if document.openai_vector_store_file_id and vector_store_id:
            try:
                client.vector_stores.files.delete(
                    document.openai_vector_store_file_id,
                    vector_store_id=vector_store_id,
                )
            except Exception:
                pass
        if document.openai_file_id:
            try:
                client.files.delete(document.openai_file_id)
            except Exception:
                pass

    def search(
        self,
        query: str,
        limit: int = 5,
        counterparty: str = "",
        doc_type_hint: str = "",
        doc_ids: Optional[List[str]] = None,
    ) -> List[RetrievedChunk]:
        vector_store_id = self.get_vector_store_id()
        if not vector_store_id:
            return []

        client = self._get_client()
        filters = self._build_filters(counterparty, doc_type_hint, doc_ids)
        kwargs: Dict[str, object] = {
            "vector_store_id": vector_store_id,
            "query": query,
            "max_num_results": limit,
            "rewrite_query": True,
        }
        if filters:
            kwargs["filters"] = filters
        response = client.vector_stores.search(**kwargs)
        results = []
        for index, item in enumerate(response.data):
            content = "\n".join(part.text for part in item.content if getattr(part, "text", ""))
            attributes = item.attributes or {}
            doc_id = str(attributes.get("doc_id", ""))
            if doc_ids and doc_id and doc_id not in doc_ids:
                continue
            results.append(
                RetrievedChunk(
                    chunk_id=f"openai:{item.file_id}:{index}",
                    doc_id=doc_id,
                    file_name=item.filename,
                    section_name=str(attributes.get("doc_type", "retrieved_context")),
                    text=content.strip(),
                    score=float(item.score),
                )
            )
        return results

    def ensure_vector_store_id(self) -> str:
        vector_store_id = self.get_vector_store_id()
        if vector_store_id:
            return vector_store_id

        client = self._get_client()
        vector_store = client.vector_stores.create(name=self.vector_store_name)
        self.store.set_state("openai_vector_store_id", vector_store.id)
        return vector_store.id

    def get_vector_store_id(self) -> str:
        if self.configured_vector_store_id:
            stored_id = self.store.get_state("openai_vector_store_id")
            if stored_id != self.configured_vector_store_id:
                self.store.set_state("openai_vector_store_id", self.configured_vector_store_id)
            return self.configured_vector_store_id
        return self.store.get_state("openai_vector_store_id")

    def _get_client(self) -> OpenAI:
        if self._client is not None:
            return self._client
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        self._client = OpenAI(api_key=api_key, base_url=self.base_url)
        return self._client

    def _build_attributes(self, document: ContractDocument) -> Dict[str, object]:
        attributes: Dict[str, object] = {
            "doc_id": document.doc_id,
            "doc_type": document.doc_type,
            "counterparty": document.counterparty_normalized,
            "doc_number": document.doc_number or "",
            "doc_date": document.doc_date or "",
            "signed_status": document.signed_status,
        }
        if document.appendix_number is not None:
            attributes["appendix_number"] = float(document.appendix_number)
        return attributes

    def _build_filters(
        self,
        counterparty: str,
        doc_type_hint: str,
        doc_ids: Optional[List[str]],
    ) -> Optional[Dict[str, object]]:
        filters: List[Dict[str, object]] = []
        if counterparty:
            filters.append(
                {
                    "type": "eq",
                    "key": "counterparty",
                    "value": counterparty,
                }
            )
        if doc_type_hint:
            filters.append(
                {
                    "type": "eq",
                    "key": "doc_type",
                    "value": doc_type_hint,
                }
            )
        if doc_ids:
            filters.append(
                {
                    "type": "in",
                    "key": "doc_id",
                    "value": doc_ids,
                }
            )
        if not filters:
            return None
        if len(filters) == 1:
            return filters[0]
        return {
            "type": "and",
            "filters": filters,
        }
