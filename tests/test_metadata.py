import unittest

from app.ingestion.metadata import extract_metadata
from app.models import RawDocument


class MetadataExtractionTests(unittest.TestCase):
    def test_extract_contract_metadata(self) -> None:
        raw_document = RawDocument(
            source_path="contract.docx",
            file_name="contract.docx",
            paragraphs=[],
            full_text=(
                "ДОГОВОР № 15/24\n"
                "от 15.03.2024\n"
                "ООО \"Ромашка\" и ООО \"Альфа\"\n"
                "Условия оплаты: постоплата 15 банковских дней."
            ),
            sha256="abc",
        )

        metadata = extract_metadata(raw_document)
        self.assertEqual(metadata.doc_type, "contract")
        self.assertEqual(metadata.doc_number, "15/24")
        self.assertEqual(metadata.doc_date, "15.03.2024")
        self.assertIn("РОМАШКА", metadata.counterparty_normalized)

    def test_extract_appendix_metadata(self) -> None:
        raw_document = RawDocument(
            source_path="appendix.docx",
            file_name="appendix.docx",
            paragraphs=[],
            full_text=(
                "Приложение № 3\n"
                "к договору № 15/24\n"
                "ООО \"Ромашка\""
            ),
            sha256="def",
        )

        metadata = extract_metadata(raw_document)
        self.assertEqual(metadata.doc_type, "appendix")
        self.assertEqual(metadata.parent_contract_number, "15/24")
        self.assertEqual(metadata.appendix_number, 3)


if __name__ == "__main__":
    unittest.main()
