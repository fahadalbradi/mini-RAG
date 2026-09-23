from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from routes import base, data, nlp
from motor.motor_asyncio import AsyncIOMotorClient
from helpers.config import get_settings
from stores.llm import LLMProviderFactory, LLMEnums
from stores.vectordb import VectorDBProviderFactory

logger = logging.getLogger("uvicorn.error")

def create_llm_client(factory: LLMProviderFactory, backend: str, warnings: list):
    """Create the requested LLM client; fall back to the offline LOCAL provider if it can't be built."""
    try:
        return backend.upper(), factory.create(provider=backend)
    except ValueError as e:
        warning = f"{e} Using the offline LOCAL provider."
        if warning not in warnings:
            warnings.append(warning)
            logger.warning(warning)
        return LLMEnums.LOCAL.value, factory.create(provider=LLMEnums.LOCAL.value)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.startup_warnings = []

    # ----- MongoDB (or an in-memory mock for quick demos / tests) -----
    if settings.MONGODB_URI.startswith("mongomock"):
        from mongomock_motor import AsyncMongoMockClient
        app.mongo_conn = AsyncMongoMockClient()
        app.database_backend = "MONGOMOCK (in-memory)"
    else:
        app.mongo_conn = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
        app.database_backend = "MONGODB"
    app.db_client = app.mongo_conn[settings.MONGODB_DATABASE]

    # ----- LLM clients -----
    llm_provider_factory = LLMProviderFactory(settings)

    app.generation_backend, app.generation_client = create_llm_client(
        llm_provider_factory, settings.GENERATION_BACKEND, app.startup_warnings)
    if app.generation_backend != LLMEnums.LOCAL.value:
        app.generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)

    app.embedding_backend, app.embedding_client = create_llm_client(
        llm_provider_factory, settings.EMBEDDING_BACKEND, app.startup_warnings)
    if app.embedding_backend != LLMEnums.LOCAL.value:
        app.embedding_client.set_embedding_model(
            model_id=settings.EMBEDDING_MODEL_ID,
            embedding_size=settings.EMBEDDING_MODEL_SIZE,
        )

    # ----- Vector DB -----
    app.vectordb_client = VectorDBProviderFactory(settings).create(provider=settings.VECTOR_DB_BACKEND)
    app.vectordb_client.connect()

    yield

    app.vectordb_client.disconnect()
    app.mongo_conn.close()

app = FastAPI(
    title="mini-RAG",
    description="A minimal Retrieval-Augmented Generation API: upload, chunk, index and ask.",
    lifespan=lifespan,
)

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    # e.g. a non-alphanumeric project_id rejected by the Project scheme
    return JSONResponse(
        status_code=422,
        content={"signal": "validation error", "detail": exc.errors(include_url=False, include_context=False)},
    )

app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)
