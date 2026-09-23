import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

class Settings(BaseSettings):
    APP_NAME: str = "mini-RAG"
    APP_VERSION: str = "0.1"

    FILE_ALLOWED_TYPES: list = ["text/plain", "application/pdf"]
    FILE_MAX_SIZE: int = 10
    FILE_DEFAULT_CHUNK_SIZE: int = 512000

    MONGODB_URI: str = "mongodb://localhost:27007"
    MONGODB_DATABASE: str = "mini-rag"

    GENERATION_BACKEND: str = "OPENAI"
    EMBEDDING_BACKEND: str = "OPENAI"

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_URL: Optional[str] = None

    GENERATION_MODEL_ID: str = "gpt-4o-mini"
    EMBEDDING_MODEL_ID: str = "text-embedding-3-small"
    EMBEDDING_MODEL_SIZE: int = 1536

    INPUT_DEFAULT_MAX_CHARACTERS: int = 4096
    GENERATION_DEFAULT_MAX_TOKENS: int = 512
    GENERATION_DEFAULT_TEMPERATURE: float = 0.1

    VECTOR_DB_BACKEND: str = "QDRANT"
    VECTOR_DB_PATH: str = "qdrant_db"
    VECTOR_DB_DISTANCE_METHOD: str = "COSINE"

    # source/.env, regardless of the directory the app is started from
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
