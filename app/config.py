from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    base_dir: Path
    db_path: Path
    qdrant_path: Path
    manual_metadata_path: Path
    qdrant_collection: str
    ollama_base_url: str
    chat_model: str
    embedding_model: str
    top_k: int

    @classmethod
    def from_env(cls) -> "Settings":
        base_dir = Path(os.getenv("BASE_DIR", Path.cwd()))
        db_path = base_dir / os.getenv("DB_PATH", "data/db/contracts.sqlite3")
        qdrant_path = base_dir / os.getenv("QDRANT_PATH", "data/db/qdrant")
        manual_metadata_path = base_dir / os.getenv(
            "MANUAL_METADATA_PATH", "data/manual_metadata.json"
        )
        return cls(
            base_dir=base_dir,
            db_path=db_path,
            qdrant_path=qdrant_path,
            manual_metadata_path=manual_metadata_path,
            qdrant_collection=os.getenv("QDRANT_COLLECTION", "contract_chunks"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            chat_model=os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:7b"),
            embedding_model=os.getenv("OLLAMA_EMBED_MODEL", "qwen3-embedding:0.6b"),
            top_k=int(os.getenv("TOP_K", "6")),
        )

    def ensure_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.qdrant_path.mkdir(parents=True, exist_ok=True)
