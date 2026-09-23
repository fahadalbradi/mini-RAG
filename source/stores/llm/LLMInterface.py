from abc import ABC, abstractmethod

class LLMInterface(ABC):

    # False for providers that can only embed (the LOCAL provider);
    # the NLPController then falls back to an extractive answer.
    can_generate: bool = True

    @abstractmethod
    def set_generation_model(self, model_id: str):
        pass

    @abstractmethod
    def set_embedding_model(self, model_id: str, embedding_size: int):
        pass

    @abstractmethod
    def generate_text(self, prompt: str, chat_history: list = None, max_output_tokens: int = None,
                      temperature: float = None):
        pass

    @abstractmethod
    def embed_texts(self, texts: list, document_type: str = None):
        pass

    def embed_text(self, text: str, document_type: str = None):
        vectors = self.embed_texts([text], document_type=document_type)
        return vectors[0] if vectors else None

    @abstractmethod
    def construct_prompt(self, prompt: str, role: str):
        pass
