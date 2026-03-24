from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from app.models import DocumentChunk, RetrievedChunk


class QdrantVectorStore:
    def __init__(self, path: Path, collection_name: str):
        self.path = path
        self.collection_name = collection_name
        self.client = self._create_client(path)
        self._vector_size: Optional[int] = None

    def _create_client(self, path: Path):
        try:
            from qdrant_client import QdrantClient  # type: ignore
        except ImportError as exc:  # pragma: no cover - dependency check
            raise RuntimeError(
                "qdrant-client is not installed. Install dependencies from requirements.txt."
            ) from exc
        return QdrantClient(path=str(path))

    def ensure_collection(self, vector_size: int) -> None:
        if self._vector_size == vector_size:
            return
        from qdrant_client.http import models as rest  # type: ignore

        collections = self.client.get_collections().collections
        existing_names = {collection.name for collection in collections}
        if self.collection_name not in existing_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=rest.VectorParams(size=vector_size, distance=rest.Distance.COSINE),
            )
        self._vector_size = vector_size

    def upsert(self, chunks: List[DocumentChunk], vectors: List[List[float]], payloads: List[Dict[str, object]]) -> None:
        if not chunks:
            return
        self.ensure_collection(len(vectors[0]))
        from qdrant_client.http import models as rest  # type: ignore

        points = []
        for chunk, vector, payload in zip(chunks, vectors, payloads):
            points.append(
                rest.PointStruct(
                    id=chunk.chunk_id,
                    vector=vector,
                    payload=payload,
                )
            )
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        doc_ids: Optional[List[str]] = None,
    ) -> List[RetrievedChunk]:
        self.ensure_collection(len(query_vector))
        query_filter = None
        if doc_ids:
            from qdrant_client.http import models as rest  # type: ignore

            query_filter = rest.Filter(
                should=[
                    rest.FieldCondition(
                        key="doc_id",
                        match=rest.MatchValue(value=doc_id),
                    )
                    for doc_id in doc_ids
                ]
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
        )
        return [
            RetrievedChunk(
                chunk_id=str(item.id),
                doc_id=str(item.payload.get("doc_id", "")),
                file_name=str(item.payload.get("file_name", "")),
                section_name=str(item.payload.get("section_name", "general")),
                text=str(item.payload.get("text", "")),
                score=float(item.score or 0.0),
            )
            for item in results
        ]
