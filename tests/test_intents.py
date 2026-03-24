import unittest

from app.retrieval.intents import classify_question


class IntentClassificationTests(unittest.TestCase):
    def test_classifies_payment_terms(self) -> None:
        intent = classify_question("какие условия постоплаты по договору с ООО Ромашка?")
        self.assertEqual(intent.name, "payment_terms")
        self.assertIn("РОМАШКА", intent.normalized_counterparty)

    def test_classifies_next_appendix_number(self) -> None:
        intent = classify_question("какой будет следующий номер Приложения с ООО Ромашка?")
        self.assertEqual(intent.name, "next_appendix_number")


if __name__ == "__main__":
    unittest.main()
