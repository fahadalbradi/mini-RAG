"""Regression: recreating a collection must not bring back old points."""
from stores.vectordb.providers import QdrantDBProvider

def test_reset_collection_drops_old_points_and_accepts_new_size(tmp_path):
    provider = QdrantDBProvider(db_path=str(tmp_path), distance_method="COSINE")
    provider.connect()
    try:
        # e.g. indexed first with LOCAL embeddings (2048-d)...
        provider.create_collection("collection_demo", embedding_size=2048)
        assert provider.insert_many("collection_demo", ["a", "b", "c"], [[0.1] * 2048] * 3)

        # ...then rebuilt with OpenAI embeddings (1536-d)
        provider.create_collection("collection_demo", embedding_size=1536, do_reset=True)
        assert provider.get_collection_info("collection_demo")["points_count"] == 0

        assert provider.insert_many("collection_demo", ["x"], [[0.1] * 1536])
        info = provider.get_collection_info("collection_demo")
        assert info["points_count"] == 1
        assert info["vector_size"] == 1536
    finally:
        provider.disconnect()
