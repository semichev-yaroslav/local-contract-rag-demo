from __future__ import annotations

from typing import Dict, Iterable, List, Protocol

from app.models import ContractDocument, QueryIntent, RetrievedChunk, SearchAnswer
from app.retrieval.intents import classify_question
from app.storage.sqlite_store import SQLiteStore
from app.storage.vector_store import QdrantVectorStore


class EmbedderProtocol(Protocol):
    def embed(self, texts: List[str]) -> List[List[float]]:
        ...


class GeneratorProtocol(Protocol):
    def answer(self, question: str, sources: Iterable[RetrievedChunk]) -> str:
        ...


class QueryService:
    def __init__(
        self,
        store: SQLiteStore,
        vector_store: QdrantVectorStore,
        embedder: EmbedderProtocol,
        generator: GeneratorProtocol,
        top_k: int = 6,
    ):
        self.store = store
        self.vector_store = vector_store
        self.embedder = embedder
        self.generator = generator
        self.top_k = top_k

    def answer(self, question: str) -> SearchAnswer:
        intent = classify_question(question)
        if intent.name == "contract_exists":
            return self._answer_contract_exists(question, intent)
        if intent.name == "signed_contract_exists":
            return self._answer_signed_contract_exists(question, intent)
        if intent.name == "contract_details":
            return self._answer_contract_details(question, intent)
        if intent.name == "next_appendix_number":
            return self._answer_next_appendix(question, intent)
        return self._answer_with_retrieval(question, intent)

    def _answer_contract_exists(self, question: str, intent: QueryIntent) -> SearchAnswer:
        documents = self.store.find_documents(counterparty=intent.counterparty)
        if not documents:
            return SearchAnswer(question, intent.name, "Подходящий договор не найден.")
        document = self._pick_primary_document(documents)
        answer = (
            f"Да, найден документ: {document.file_name}. "
            f"Тип: {document.doc_type}, номер: {document.doc_number or 'не указан'}, "
            f"дата: {document.doc_date or 'не указана'}."
        )
        return SearchAnswer(question, intent.name, answer)

    def _answer_signed_contract_exists(self, question: str, intent: QueryIntent) -> SearchAnswer:
        documents = self.store.find_documents(counterparty=intent.counterparty, signed_only=True)
        if not documents:
            return SearchAnswer(
                question,
                intent.name,
                "Подписанный договор не найден. В MVP статус подписи определяется только по ручному override или явному признаку в тексте.",
            )
        document = self._pick_primary_document(documents)
        answer = (
            f"Да, найден подписанный документ: {document.file_name}. "
            f"Номер: {document.doc_number or 'не указан'}, дата: {document.doc_date or 'не указана'}."
        )
        return SearchAnswer(question, intent.name, answer)

    def _answer_contract_details(self, question: str, intent: QueryIntent) -> SearchAnswer:
        documents = self.store.find_documents(
            counterparty=intent.counterparty,
            doc_type_hint="contract",
        )
        if not documents:
            return SearchAnswer(question, intent.name, "Договор по указанному контрагенту не найден.")
        document = self._pick_primary_document(documents)
        answer = (
            f"Найден договор {document.doc_number or 'без номера'} "
            f"от {document.doc_date or 'дата не указана'} "
            f"с контрагентом {document.counterparty_raw or 'не определен'}."
        )
        return SearchAnswer(question, intent.name, answer)

    def _answer_next_appendix(self, question: str, intent: QueryIntent) -> SearchAnswer:
        numbers = self.store.get_appendix_numbers(intent.counterparty)
        next_number = (max(numbers) + 1) if numbers else 1
        answer = (
            f"Следующий номер приложения для контрагента "
            f"{intent.counterparty or 'не указан'}: {next_number}."
        )
        return SearchAnswer(question, intent.name, answer)

    def _answer_with_retrieval(self, question: str, intent: QueryIntent) -> SearchAnswer:
        scoped_docs = self.store.find_documents(counterparty=intent.counterparty) if intent.counterparty else []
        doc_ids = [document.doc_id for document in scoped_docs]

        keyword_sources = self.store.search_chunks_fts(
            self._fts_query(question),
            doc_ids=doc_ids or None,
            section_hint=intent.section_hint,
            limit=self.top_k,
        )
        query_vector = self.embedder.embed([question])[0]
        vector_sources = self.vector_store.search(query_vector, limit=self.top_k, doc_ids=doc_ids or None)

        merged_sources = self._merge_sources(keyword_sources, vector_sources)
        if not merged_sources:
            return SearchAnswer(question, intent.name, "Не удалось найти релевантные фрагменты в документах.")

        try:
            answer = self.generator.answer(question, merged_sources[: self.top_k])
            used_llm = True
        except Exception:
            answer = self._fallback_answer(question, merged_sources[: self.top_k])
            used_llm = False

        return SearchAnswer(
            question=question,
            intent=intent.name,
            answer=answer,
            sources=merged_sources[: self.top_k],
            used_llm=used_llm,
        )

    def _pick_primary_document(self, documents: Iterable[ContractDocument]) -> ContractDocument:
        return sorted(
            documents,
            key=lambda document: (
                document.doc_date or "",
                document.created_at,
                document.doc_number or "",
            ),
            reverse=True,
        )[0]

    def _merge_sources(
        self, keyword_sources: List[RetrievedChunk], vector_sources: List[RetrievedChunk]
    ) -> List[RetrievedChunk]:
        merged: Dict[str, RetrievedChunk] = {}
        for index, source in enumerate(keyword_sources):
            merged[source.chunk_id] = RetrievedChunk(
                chunk_id=source.chunk_id,
                doc_id=source.doc_id,
                file_name=source.file_name,
                section_name=source.section_name,
                text=source.text,
                score=2.0 - (index * 0.05),
            )
        for index, source in enumerate(vector_sources):
            current = merged.get(source.chunk_id)
            adjusted_score = source.score + max(0.0, 1.0 - index * 0.05)
            if current:
                current.score += adjusted_score
                continue
            merged[source.chunk_id] = RetrievedChunk(
                chunk_id=source.chunk_id,
                doc_id=source.doc_id,
                file_name=source.file_name,
                section_name=source.section_name,
                text=source.text,
                score=adjusted_score,
            )
        return sorted(merged.values(), key=lambda item: item.score, reverse=True)

    def _fallback_answer(self, question: str, sources: List[RetrievedChunk]) -> str:
        snippets = []
        for source in sources[:3]:
            snippets.append(
                f"- {source.file_name} / {source.section_name}: {source.text[:280].strip()}"
            )
        context = "\n".join(snippets)
        return f"Найдены релевантные фрагменты по вопросу «{question}»:\n{context}"

    def _fts_query(self, question: str) -> str:
        tokens = [token.strip(" ?!.,:;()").lower() for token in question.split()]
        tokens = [token for token in tokens if len(token) > 2]
        return " OR ".join(tokens[:8]) or question
