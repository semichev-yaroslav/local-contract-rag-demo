from __future__ import annotations

import os
from typing import Iterable

from openai import OpenAI

from app.models import RetrievedChunk


SYSTEM_PROMPT = """Ты помощник по договорам.
Отвечай только по предоставленному контексту.
Если данных недостаточно, так и скажи.
Если можешь, укажи номер договора, дату и источник."""


class OpenAIChatClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client: OpenAI | None = None

    def answer(self, question: str, sources: Iterable[RetrievedChunk]) -> str:
        context = []
        for index, source in enumerate(sources, start=1):
            context.append(
                f"[{index}] Файл: {source.file_name}\n"
                f"Раздел: {source.section_name}\n"
                f"Текст:\n{source.text}"
            )
        prompt = "\n\n".join(context) or "Контекст отсутствует."

        response = self._get_client().responses.create(
            model=self.model,
            instructions=SYSTEM_PROMPT,
            input=f"Вопрос: {question}\n\nКонтекст:\n{prompt}",
            temperature=0.1,
            max_output_tokens=600,
        )
        output_text = getattr(response, "output_text", "")
        if output_text:
            return output_text.strip()
        payload = response.model_dump()
        return str(payload)

    def _get_client(self) -> OpenAI:
        if self._client is not None:
            return self._client
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        self._client = OpenAI(api_key=api_key, base_url=self.base_url)
        return self._client
