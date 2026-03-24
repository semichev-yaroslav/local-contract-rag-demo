from __future__ import annotations

from typing import Iterable

import requests

from app.models import RetrievedChunk


SYSTEM_PROMPT = """Ты помощник по договорам.
Отвечай только по предоставленному контексту.
Если данных недостаточно, так и скажи.
Если можешь, укажи номер договора, дату и источник."""


class OllamaChatClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def answer(self, question: str, sources: Iterable[RetrievedChunk]) -> str:
        context = []
        for index, source in enumerate(sources, start=1):
            context.append(
                f"[{index}] Файл: {source.file_name}\n"
                f"Раздел: {source.section_name}\n"
                f"Текст:\n{source.text}"
            )
        prompt = "\n\n".join(context) or "Контекст отсутствует."

        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Вопрос: {question}\n\nКонтекст:\n{prompt}",
                    },
                ],
            },
            timeout=180,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["message"]["content"].strip()
