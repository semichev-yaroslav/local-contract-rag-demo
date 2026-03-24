import tempfile
import unittest
from pathlib import Path

from app.models import ContractDocument, DocumentChunk, RetrievedChunk
from app.retrieval.service import QueryService
from app.storage.sqlite_store import SQLiteStore


class FakeGenerator:
    def answer(self, question, sources):
        return f"Сводка по вопросу: {question}. Источников: {len(list(sources))}."


class FakeRetriever:
    def __init__(self, results):
        self.results = results

    def search(self, query, limit=5, counterparty="", doc_type_hint="", doc_ids=None):
        if doc_ids:
            return [item for item in self.results if item.doc_id in doc_ids][:limit]
        return self.results[:limit]


class QueryServiceTests(unittest.TestCase):
    def test_answers_structured_contract_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "contracts.sqlite3")
            document = ContractDocument(
                doc_id="doc-1",
                source_path="contract.docx",
                file_name="contract.docx",
                sha256="sha-1",
                doc_type="contract",
                counterparty_raw='ООО "Ромашка"',
                counterparty_normalized="ООО РОМАШКА",
                doc_number="15/24",
                doc_date="15.03.2024",
                parent_contract_number="",
                appendix_number=None,
                signed_status="signed",
                full_text="Договор поставки. Условия оплаты: постоплата 15 банковских дней.",
                extraction_confidence=1.0,
                created_at="2024-03-15T00:00:00+00:00",
            )
            chunks = [
                DocumentChunk(
                    chunk_id="doc-1:0",
                    doc_id="doc-1",
                    chunk_order=0,
                    section_name="Порядок расчетов",
                    text="Постоплата 15 банковских дней с даты получения счета.",
                )
            ]
            store.upsert_document(document, chunks)
            service = QueryService(
                store=store,
                vector_store=FakeRetriever(
                    [
                        RetrievedChunk(
                            chunk_id="doc-1:0",
                            doc_id="doc-1",
                            file_name="contract.docx",
                            section_name="Порядок расчетов",
                            text=chunks[0].text,
                            score=0.9,
                        )
                    ]
                ),
                generator=FakeGenerator(),
            )

            answer = service.answer("какой номер и дата договора с ООО Ромашка?")
            self.assertEqual(answer.intent, "contract_details")
            self.assertIn("15/24", answer.answer)
            self.assertIn("15.03.2024", answer.answer)

    def test_answers_payment_terms_with_retrieval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "contracts.sqlite3")
            document = ContractDocument(
                doc_id="doc-2",
                source_path="contract2.docx",
                file_name="contract2.docx",
                sha256="sha-2",
                doc_type="contract",
                counterparty_raw='ООО "Ромашка"',
                counterparty_normalized="ООО РОМАШКА",
                doc_number="16/24",
                doc_date="20.03.2024",
                parent_contract_number="",
                appendix_number=None,
                signed_status="unknown",
                full_text="Условия оплаты: постоплата 10 банковских дней.",
                extraction_confidence=1.0,
                created_at="2024-03-20T00:00:00+00:00",
            )
            chunks = [
                DocumentChunk(
                    chunk_id="doc-2:0",
                    doc_id="doc-2",
                    chunk_order=0,
                    section_name="Условия оплаты",
                    text="Постоплата 10 банковских дней после подписания акта.",
                )
            ]
            store.upsert_document(document, chunks)
            service = QueryService(
                store=store,
                vector_store=FakeRetriever(
                    [
                        RetrievedChunk(
                            chunk_id="doc-2:0",
                            doc_id="doc-2",
                            file_name="contract2.docx",
                            section_name="Условия оплаты",
                            text=chunks[0].text,
                            score=0.95,
                        )
                    ]
                ),
                generator=FakeGenerator(),
            )

            answer = service.answer("какие условия постоплаты по договору с ООО Ромашка?")
            self.assertEqual(answer.intent, "payment_terms")
            self.assertTrue(answer.used_llm)
            self.assertEqual(len(answer.sources), 1)
            self.assertIn("Источников: 1", answer.answer)


if __name__ == "__main__":
    unittest.main()
