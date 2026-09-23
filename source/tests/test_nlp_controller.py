"""Unit tests for the generation path (no network: fake LLM + fake vector DB)."""
from controllers import NLPController
from models.db_schemes import Project, RetrievedDocument
from stores.llm.providers import LocalProvider

class FakeVectorDB:
    def is_collection_existed(self, collection_name):
        return True

    def search_by_vector(self, collection_name, vector, limit):
        return [
            RetrievedDocument(text="Alan is a young scholar.", score=0.9, metadata={"source": "a.txt"}),
            RetrievedDocument(text="The village sits in a valley.", score=0.5, metadata={"source": "a.txt"}),
        ][:limit]

class FakeLLM(LocalProvider):
    can_generate = True

    def __init__(self):
        super().__init__()
        self.calls = []

    def generate_text(self, prompt, chat_history=None, max_output_tokens=None, temperature=None):
        self.calls.append((prompt, chat_history))
        return "Alan is a young scholar [1]."

def test_answer_uses_generation_client_with_numbered_documents():
    llm = FakeLLM()
    controller = NLPController(vectordb_client=FakeVectorDB(), generation_client=llm, embedding_client=llm)

    answer, full_prompt, chat_history, documents = controller.answer_rag_question(
        project=Project(project_id="demo"), query="Who is Alan?", limit=2)

    assert answer == "Alan is a young scholar [1]."
    assert "## Document [1]\nAlan is a young scholar." in full_prompt
    assert "## Document [2]" in full_prompt
    assert full_prompt.rstrip().endswith("## Answer:")
    assert chat_history[0]["role"] == "system"
    assert len(documents) == 2
    assert len(llm.calls) == 1

def test_extractive_answer_cites_matching_sentence():
    controller = NLPController(vectordb_client=FakeVectorDB(), generation_client=LocalProvider(),
                               embedding_client=LocalProvider())
    answer, full_prompt, _, _ = controller.answer_rag_question(
        project=Project(project_id="demo"), query="Where is the village?", limit=2)

    assert answer == "The village sits in a valley. [2]"
    assert full_prompt is None
