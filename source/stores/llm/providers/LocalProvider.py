from ..LLMInterface import LLMInterface
import hashlib
import re
import numpy as np

class LocalProvider(LLMInterface):
    """Offline provider: no API key, no model download.

    Embeddings are feature-hashed word unigrams + bigrams (a lexical signal,
    not a semantic one), which is enough to demo the full pipeline.
    It cannot generate text, so answers are built extractively by the NLPController.
    """

    can_generate = False

    TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)

    STOPWORDS = frozenset("""
        a an and are as at be been but by can could did do does for from had has have he her him his
        how i if in into is it its me my of on or our she so than that the their them then there these
        they this to was we were what when where which who whom why will with would you your
    """.split())

    def __init__(self, embedding_size: int = 2048):
        self.embedding_size = embedding_size
        self.embedding_model_id = "local-hashing"
        self.generation_model_id = None

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def generate_text(self, prompt: str, chat_history: list = None, max_output_tokens: int = None,
                      temperature: float = None):
        return None

    @classmethod
    def tokenize(cls, text: str):
        tokens = (token.lower() for token in cls.TOKEN_PATTERN.findall(text))
        return [token for token in tokens if len(token) > 1 and token not in cls.STOPWORDS]

    def _bucket(self, feature: str):
        # Unsigned buckets: a collision can only add noise, never cancel a real match.
        digest = hashlib.md5(feature.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "little") % self.embedding_size

    def _embed(self, text: str):
        vector = np.zeros(self.embedding_size, dtype=np.float32)
        tokens = self.tokenize(text)
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        for feature in features:
            vector[self._bucket(feature)] += 1.0

        # sublinear term frequency, then L2-normalize
        vector = np.log1p(vector)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm
        return vector.tolist()

    def embed_texts(self, texts: list, document_type: str = None):
        return [self._embed(text) for text in texts]

    def construct_prompt(self, prompt: str, role: str):
        return {"role": role, "content": prompt}
