import os
import shutil
import sys
import tempfile
import pytest

# Run fully offline: in-memory MongoDB, LOCAL embeddings/answers, throwaway Qdrant folder.
TEST_DB_DIR = tempfile.mkdtemp(prefix="minirag_qdrant_")
os.environ.update({
    "MONGODB_URI": "mongomock://",
    "MONGODB_DATABASE": "mini-rag-test",
    "GENERATION_BACKEND": "LOCAL",
    "EMBEDDING_BACKEND": "LOCAL",
    "VECTOR_DB_PATH": TEST_DB_DIR,
})

SOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SOURCE_DIR)

@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as test_client:
        yield test_client

    shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

@pytest.fixture(scope="session")
def sample_file():
    return os.path.join(os.path.dirname(SOURCE_DIR), "samples", "story.txt")

@pytest.fixture(scope="session")
def project_id():
    project_id = "pytest" + os.urandom(4).hex()
    yield project_id
    shutil.rmtree(os.path.join(SOURCE_DIR, "assets", "files", project_id), ignore_errors=True)
