from .BaseController import BaseController
from models.db_schemes import Project, DataChunk, RetrievedDocument
from stores.llm.LLMEnums import DocumentTypeEnum, OpenAIEnums
from stores.llm.providers import LocalProvider
from stores.llm.templates import rag
from typing import List
import re

class NLPController(BaseController):

    def __init__(self, vectordb_client, generation_client, embedding_client):
        super().__init__()
        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client

    def create_collection_name(self, project_id: str):
        return f"collection_{project_id}".strip()

    def reset_vector_db_collection(self, project: Project):
        collection_name = self.create_collection_name(project_id=project.project_id)
        return self.vectordb_client.delete_collection(collection_name=collection_name)

    def get_vector_db_collection_info(self, project: Project):
        collection_name = self.create_collection_name(project_id=project.project_id)
        if not self.vectordb_client.is_collection_existed(collection_name):
            return None
        return self.vectordb_client.get_collection_info(collection_name=collection_name)

    def index_into_vector_db(self, project: Project, chunks: List[DataChunk], chunks_ids: List[int],
                             do_reset: bool = False):
        collection_name = self.create_collection_name(project_id=project.project_id)

        texts = [chunk.chunk_text for chunk in chunks]
        metadata = [chunk.chunk_metadata for chunk in chunks]
        vectors = self.embedding_client.embed_texts(texts, document_type=DocumentTypeEnum.DOCUMENT.value)
        if not vectors:
            return False

        self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=len(vectors[0]),
            do_reset=do_reset,
        )

        return self.vectordb_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            vectors=vectors,
            metadata=metadata,
            record_ids=chunks_ids,
        )

    def search_vector_db_collection(self, project: Project, text: str, limit: int = 5):
        collection_name = self.create_collection_name(project_id=project.project_id)
        if not self.vectordb_client.is_collection_existed(collection_name):
            return None

        vector = self.embedding_client.embed_text(text=text, document_type=DocumentTypeEnum.QUERY.value)
        if not vector:
            return None

        results = self.vectordb_client.search_by_vector(
            collection_name=collection_name,
            vector=vector,
            limit=limit,
        )
        return results or None

    def answer_rag_question(self, project: Project, query: str, limit: int = 5):
        """Returns (answer, full_prompt, chat_history, retrieved_documents)."""

        retrieved_documents = self.search_vector_db_collection(project=project, text=query, limit=limit)
        if not retrieved_documents:
            return None, None, None, None

        if not self.generation_client.can_generate:
            answer = self.build_extractive_answer(query=query, documents=retrieved_documents)
            return answer, None, None, retrieved_documents

        system_prompt = rag.system_prompt
        documents_prompts = "\n".join([
            rag.document_prompt.substitute(doc_num=idx + 1, chunk_text=doc.text)
            for idx, doc in enumerate(retrieved_documents)
        ])
        footer_prompt = rag.footer_prompt.substitute(query=query)

        chat_history = [
            self.generation_client.construct_prompt(prompt=system_prompt, role=OpenAIEnums.SYSTEM.value),
        ]
        full_prompt = "\n\n".join([documents_prompts, footer_prompt])

        answer = self.generation_client.generate_text(prompt=full_prompt, chat_history=chat_history)

        return answer, full_prompt, chat_history, retrieved_documents

    def build_extractive_answer(self, query: str, documents: List[RetrievedDocument], max_sentences: int = 3):
        """Offline fallback: pick the retrieved sentences that best overlap the question."""

        query_terms = set(LocalProvider.tokenize(query))
        candidates = []
        for doc_idx, doc in enumerate(documents):
            for sent_idx, sentence in enumerate(re.split(r"(?<=[.!?])\s+|\n+", doc.text)):
                sentence = sentence.strip()
                if len(sentence) < 20:
                    continue
                overlap = len(query_terms & set(LocalProvider.tokenize(sentence)))
                if overlap:
                    candidates.append((overlap + doc.score, doc_idx, sent_idx, sentence))

        if not candidates:
            return (f"I could not find a direct answer. The most relevant passage is [1]:\n\n"
                    f"> {documents[0].text.strip()}")

        best, seen = [], set()
        for candidate in sorted(candidates, reverse=True):
            if candidate[3] not in seen:  # the same text can be retrieved from overlapping/duplicate chunks
                seen.add(candidate[3])
                best.append(candidate)
            if len(best) == max_sentences:
                break
        best.sort(key=lambda item: (item[1], item[2]))  # keep reading order
        return " ".join(f"{sentence} [{doc_idx + 1}]" for _, doc_idx, _, sentence in best)
