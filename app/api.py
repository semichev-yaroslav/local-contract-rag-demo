from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.bootstrap import build_runtime


app = FastAPI(title="Local Contract RAG")


class AskRequest(BaseModel):
    question: str


runtime = build_runtime()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ingest")
def ingest(payload: dict) -> dict:
    path = payload.get("path")
    if not path:
        raise HTTPException(status_code=400, detail="Missing 'path'")
    return runtime["ingestion"].ingest_path(runtime["settings"].base_dir / path)


@app.post("/ask")
def ask(request: AskRequest) -> dict:
    answer = runtime["query"].answer(request.question)
    return {
        "intent": answer.intent,
        "answer": answer.answer,
        "used_llm": answer.used_llm,
        "sources": [
            {
                "file_name": source.file_name,
                "section_name": source.section_name,
                "score": source.score,
                "text": source.text,
            }
            for source in answer.sources
        ],
    }
