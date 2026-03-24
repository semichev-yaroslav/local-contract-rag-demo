from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional

from app.models import ContractDocument, DocumentChunk, RetrievedChunk
from app.utils.text import normalize_counterparty


class SQLiteStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection = sqlite3.connect(str(db_path))
        self.connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                source_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                sha256 TEXT NOT NULL UNIQUE,
                doc_type TEXT NOT NULL,
                counterparty_raw TEXT,
                counterparty_normalized TEXT,
                doc_number TEXT,
                doc_date TEXT,
                parent_contract_number TEXT,
                appendix_number INTEGER,
                signed_status TEXT,
                full_text TEXT NOT NULL,
                extraction_confidence REAL NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                chunk_order INTEGER NOT NULL,
                section_name TEXT NOT NULL,
                text TEXT NOT NULL,
                FOREIGN KEY(doc_id) REFERENCES documents(doc_id)
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                doc_id UNINDEXED,
                file_name,
                counterparty_normalized,
                doc_number,
                full_text
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                doc_id UNINDEXED,
                section_name,
                text
            );
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def has_document(self, sha256: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM documents WHERE sha256 = ? LIMIT 1", (sha256,)
        ).fetchone()
        return row is not None

    def delete_document_by_sha256(self, sha256: str) -> None:
        row = self.connection.execute(
            "SELECT doc_id FROM documents WHERE sha256 = ? LIMIT 1", (sha256,)
        ).fetchone()
        if not row:
            return
        doc_id = row["doc_id"]
        self.connection.execute("DELETE FROM chunks_fts WHERE doc_id = ?", (doc_id,))
        self.connection.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        self.connection.execute("DELETE FROM documents_fts WHERE doc_id = ?", (doc_id,))
        self.connection.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        self.connection.commit()

    def upsert_document(self, document: ContractDocument, chunks: Iterable[DocumentChunk]) -> None:
        self.connection.execute(
            """
            INSERT INTO documents (
                doc_id, source_path, file_name, sha256, doc_type, counterparty_raw,
                counterparty_normalized, doc_number, doc_date, parent_contract_number,
                appendix_number, signed_status, full_text, extraction_confidence, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
                source_path = excluded.source_path,
                file_name = excluded.file_name,
                sha256 = excluded.sha256,
                doc_type = excluded.doc_type,
                counterparty_raw = excluded.counterparty_raw,
                counterparty_normalized = excluded.counterparty_normalized,
                doc_number = excluded.doc_number,
                doc_date = excluded.doc_date,
                parent_contract_number = excluded.parent_contract_number,
                appendix_number = excluded.appendix_number,
                signed_status = excluded.signed_status,
                full_text = excluded.full_text,
                extraction_confidence = excluded.extraction_confidence,
                created_at = excluded.created_at
            """,
            (
                document.doc_id,
                document.source_path,
                document.file_name,
                document.sha256,
                document.doc_type,
                document.counterparty_raw,
                document.counterparty_normalized,
                document.doc_number,
                document.doc_date,
                document.parent_contract_number,
                document.appendix_number,
                document.signed_status,
                document.full_text,
                document.extraction_confidence,
                document.created_at,
            ),
        )
        self.connection.execute("DELETE FROM documents_fts WHERE doc_id = ?", (document.doc_id,))
        self.connection.execute(
            """
            INSERT INTO documents_fts (doc_id, file_name, counterparty_normalized, doc_number, full_text)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                document.doc_id,
                document.file_name,
                document.counterparty_normalized,
                document.doc_number,
                document.full_text,
            ),
        )

        self.connection.execute("DELETE FROM chunks WHERE doc_id = ?", (document.doc_id,))
        self.connection.execute("DELETE FROM chunks_fts WHERE doc_id = ?", (document.doc_id,))
        for chunk in chunks:
            self.connection.execute(
                """
                INSERT INTO chunks (chunk_id, doc_id, chunk_order, section_name, text)
                VALUES (?, ?, ?, ?, ?)
                """,
                (chunk.chunk_id, chunk.doc_id, chunk.chunk_order, chunk.section_name, chunk.text),
            )
            self.connection.execute(
                """
                INSERT INTO chunks_fts (chunk_id, doc_id, section_name, text)
                VALUES (?, ?, ?, ?)
                """,
                (chunk.chunk_id, chunk.doc_id, chunk.section_name, chunk.text),
            )
        self.connection.commit()

    def list_documents(self) -> List[ContractDocument]:
        rows = self.connection.execute(
            "SELECT * FROM documents ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_document(row) for row in rows]

    def find_documents(
        self,
        counterparty: str = "",
        doc_type_hint: str = "",
        signed_only: bool = False,
    ) -> List[ContractDocument]:
        query = "SELECT * FROM documents WHERE 1=1"
        params = []
        if counterparty:
            normalized = normalize_counterparty(counterparty)
            query += " AND (counterparty_normalized LIKE ? OR counterparty_raw LIKE ?)"
            params.extend([f"%{normalized}%", f"%{counterparty}%"])
        if doc_type_hint:
            query += " AND doc_type = ?"
            params.append(doc_type_hint)
        if signed_only:
            query += " AND signed_status = 'signed'"
        query += " ORDER BY doc_date DESC, created_at DESC"
        rows = self.connection.execute(query, params).fetchall()
        return [self._row_to_document(row) for row in rows]

    def find_document_by_id(self, doc_id: str) -> Optional[ContractDocument]:
        row = self.connection.execute(
            "SELECT * FROM documents WHERE doc_id = ? LIMIT 1", (doc_id,)
        ).fetchone()
        return self._row_to_document(row) if row else None

    def search_documents_fts(self, query_text: str, limit: int = 5) -> List[ContractDocument]:
        rows = self.connection.execute(
            """
            SELECT d.*
            FROM documents_fts f
            JOIN documents d ON d.doc_id = f.doc_id
            WHERE documents_fts MATCH ?
            LIMIT ?
            """,
            (query_text, limit),
        ).fetchall()
        return [self._row_to_document(row) for row in rows]

    def search_chunks_fts(
        self,
        query_text: str,
        doc_ids: Optional[List[str]] = None,
        section_hint: str = "",
        limit: int = 5,
    ) -> List[RetrievedChunk]:
        sql = """
            SELECT c.chunk_id, c.doc_id, d.file_name, c.section_name, c.text
            FROM chunks_fts f
            JOIN chunks c ON c.chunk_id = f.chunk_id
            JOIN documents d ON d.doc_id = c.doc_id
            WHERE chunks_fts MATCH ?
        """
        params: List[object] = [query_text]
        if doc_ids:
            placeholders = ",".join("?" for _ in doc_ids)
            sql += f" AND c.doc_id IN ({placeholders})"
            params.extend(doc_ids)
        if section_hint:
            sql += " AND lower(c.section_name) LIKE ?"
            params.append(f"%{section_hint.lower()}%")
        sql += " LIMIT ?"
        params.append(limit)
        rows = self.connection.execute(sql, params).fetchall()
        return [
            RetrievedChunk(
                chunk_id=row["chunk_id"],
                doc_id=row["doc_id"],
                file_name=row["file_name"],
                section_name=row["section_name"],
                text=row["text"],
                score=1.0,
            )
            for row in rows
        ]

    def get_appendix_numbers(self, counterparty: str) -> List[int]:
        rows = self.connection.execute(
            """
            SELECT appendix_number
            FROM documents
            WHERE doc_type = 'appendix'
              AND counterparty_normalized LIKE ?
              AND appendix_number IS NOT NULL
            ORDER BY appendix_number ASC
            """,
            (f"%{normalize_counterparty(counterparty)}%",),
        ).fetchall()
        return [int(row["appendix_number"]) for row in rows]

    def _row_to_document(self, row: sqlite3.Row) -> ContractDocument:
        return ContractDocument(
            doc_id=row["doc_id"],
            source_path=row["source_path"],
            file_name=row["file_name"],
            sha256=row["sha256"],
            doc_type=row["doc_type"],
            counterparty_raw=row["counterparty_raw"] or "",
            counterparty_normalized=row["counterparty_normalized"] or "",
            doc_number=row["doc_number"] or "",
            doc_date=row["doc_date"] or "",
            parent_contract_number=row["parent_contract_number"] or "",
            appendix_number=row["appendix_number"],
            signed_status=row["signed_status"] or "unknown",
            full_text=row["full_text"],
            extraction_confidence=float(row["extraction_confidence"]),
            created_at=row["created_at"],
        )
