from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.bootstrap import build_runtime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local contract RAG demo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Index DOCX documents")
    ingest_parser.add_argument("path", help="Path to DOCX file or directory")
    ingest_parser.add_argument("--force", action="store_true", help="Reindex even if file hash exists")

    ask_parser = subparsers.add_parser("ask", help="Ask a question")
    ask_parser.add_argument("question", help="Question in natural language")

    subparsers.add_parser("list", help="List indexed documents")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    runtime = build_runtime()

    if args.command == "ingest":
        result = runtime["ingestion"].ingest_path(Path(args.path), force=args.force)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "ask":
        answer = runtime["query"].answer(args.question)
        payload = {
            "intent": answer.intent,
            "used_llm": answer.used_llm,
            "answer": answer.answer,
            "sources": [
                {
                    "file_name": source.file_name,
                    "section_name": source.section_name,
                    "score": source.score,
                }
                for source in answer.sources
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if args.command == "list":
        documents = runtime["store"].list_documents()
        payload = [
            {
                "file_name": document.file_name,
                "doc_type": document.doc_type,
                "counterparty": document.counterparty_raw,
                "doc_number": document.doc_number,
                "doc_date": document.doc_date,
            }
            for document in documents
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return


if __name__ == "__main__":
    main()
