from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    base_dir: Path
    db_path: Path
    manual_metadata_path: Path
    openai_base_url: str
    chat_model: str
    vector_store_name: str
    vector_store_id: str
    top_k: int

    @classmethod
    def from_env(cls) -> "Settings":
        base_dir = Path(os.getenv("BASE_DIR", Path.cwd()))
        db_path = base_dir / os.getenv("DB_PATH", "data/db/contracts.sqlite3")
        manual_metadata_path = base_dir / os.getenv(
            "MANUAL_METADATA_PATH", "data/manual_metadata.json"
        )
        return cls(
            base_dir=base_dir,
            db_path=db_path,
            manual_metadata_path=manual_metadata_path,
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5-mini"),
            vector_store_name=os.getenv("OPENAI_VECTOR_STORE_NAME", "contract-knowledge-base"),
            vector_store_id=os.getenv("OPENAI_VECTOR_STORE_ID", ""),
            top_k=int(os.getenv("TOP_K", "6")),
        )

    def ensure_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
