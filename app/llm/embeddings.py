from __future__ import annotations

from typing import List

import requests


class OllamaEmbeddingClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def embed(self, texts: List[str]) -> List[List[float]]:
        response = requests.post(
            f"{self.base_url}/api/embed",
            json={"model": self.model, "input": texts},
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        if "embeddings" not in payload:
            raise RuntimeError(f"Unexpected Ollama embed response: {payload}")
        return payload["embeddings"]
