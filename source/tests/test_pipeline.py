"""End-to-end: upload -> process -> index -> search -> answer."""

def test_welcome(client):
    response = client.get("/api/v1/")
    assert response.status_code == 200
    body = response.json()
    assert body["generation_backend"] == "LOCAL"
    assert body["embedding_backend"] == "LOCAL"

def test_rejects_unsupported_file_type(client, project_id):
    response = client.post(
        f"/api/v1/data/upload/{project_id}",
        files={"file": ("image.png", b"\x89PNG", "image/png")},
    )
    assert response.status_code == 400
    assert response.json()["signal"] == "file type is not supported"

def test_rejects_invalid_project_id(client):
    response = client.post(
        "/api/v1/data/upload/bad-id",
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 422

def test_full_rag_pipeline(client, project_id, sample_file):
    # 1) upload
    with open(sample_file, "rb") as f:
        response = client.post(
            f"/api/v1/data/upload/{project_id}",
            files={"file": ("story.txt", f, "text/plain")},
        )
    assert response.status_code == 200, response.text
    file_id = response.json()["file_id"]
    assert file_id.endswith("_story.txt")

    # 2) assets listed
    response = client.get(f"/api/v1/data/assets/{project_id}")
    assert [asset["file_id"] for asset in response.json()["assets"]] == [file_id]

    # 3) process into chunks
    response = client.post(
        f"/api/v1/data/process/{project_id}",
        json={"chunk_size": 400, "overlap": 50, "do_reset": 1},
    )
    assert response.status_code == 200, response.text
    inserted_chunks = response.json()["inserted_chunks"]
    assert inserted_chunks > 1

    # 4) push into the vector DB
    response = client.post(f"/api/v1/nlp/index/push/{project_id}", json={"do_reset": 1})
    assert response.status_code == 200, response.text
    assert response.json()["inserted_items_count"] == inserted_chunks

    response = client.get(f"/api/v1/nlp/index/info/{project_id}")
    assert response.json()["collection_info"]["points_count"] == inserted_chunks

    # 5) semantic search
    response = client.post(f"/api/v1/nlp/index/search/{project_id}", json={"text": "Who is Alan?", "limit": 3})
    assert response.status_code == 200, response.text
    results = response.json()["results"]
    assert len(results) == 3
    assert results[0]["metadata"]["source"] == file_id

    # 6) answer (extractive in LOCAL mode)
    response = client.post(f"/api/v1/nlp/index/answer/{project_id}", json={"text": "Who is Alan?"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert "Alan" in body["answer"]
    assert body["documents"]

def test_search_on_unindexed_project_fails_cleanly(client):
    response = client.post("/api/v1/nlp/index/search/neverindexed", json={"text": "anything"})
    assert response.status_code == 400
