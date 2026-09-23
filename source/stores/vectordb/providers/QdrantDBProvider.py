from qdrant_client import QdrantClient, models
from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import DistanceMethodEnums
from models.db_schemes import RetrievedDocument
import logging

class QdrantDBProvider(VectorDBInterface):
    """Embedded (on-disk) Qdrant: no server to run."""

    def __init__(self, db_path: str, distance_method: str):
        self.client = None
        self.db_path = db_path
        self.distance_method = {
            DistanceMethodEnums.COSINE.value: models.Distance.COSINE,
            DistanceMethodEnums.DOT.value: models.Distance.DOT,
        }.get(distance_method.upper(), models.Distance.COSINE)
        self.logger = logging.getLogger(__name__)

    def connect(self):
        self.client = QdrantClient(path=self.db_path)

    def disconnect(self):
        if self.client is not None:
            self.client.close()
        self.client = None

    def is_collection_existed(self, collection_name: str) -> bool:
        return self.client.collection_exists(collection_name=collection_name)

    def list_all_collections(self):
        return [collection.name for collection in self.client.get_collections().collections]

    def get_collection_info(self, collection_name: str) -> dict:
        info = self.client.get_collection(collection_name=collection_name)
        vectors_config = info.config.params.vectors
        return {
            "status": str(getattr(info.status, "value", info.status)),
            "points_count": self.client.count(collection_name=collection_name, exact=True).count,
            "vector_size": getattr(vectors_config, "size", None),
            "distance": str(getattr(getattr(vectors_config, "distance", None), "value", "")),
        }

    def delete_collection(self, collection_name: str):
        if self.is_collection_existed(collection_name):
            return self.client.delete_collection(collection_name=collection_name)

    def create_collection(self, collection_name: str, embedding_size: int, do_reset: bool = False):
        if do_reset:
            self.delete_collection(collection_name=collection_name)

        if not self.is_collection_existed(collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=embedding_size, distance=self.distance_method),
            )
            return True

        return False

    def insert_many(self, collection_name: str, texts: list, vectors: list,
                    metadata: list = None, record_ids: list = None, batch_size: int = 50):

        metadata = metadata or [None] * len(texts)
        record_ids = record_ids or list(range(len(texts)))

        for i in range(0, len(texts), batch_size):
            points = [
                models.PointStruct(
                    id=record_ids[x],
                    vector=vectors[x],
                    payload={"text": texts[x], "metadata": metadata[x]},
                )
                for x in range(i, min(i + batch_size, len(texts)))
            ]
            try:
                self.client.upsert(collection_name=collection_name, points=points)
            except Exception as e:
                self.logger.error(f"Error while inserting batch into Qdrant: {e}")
                return False

        return True

    def search_by_vector(self, collection_name: str, vector: list, limit: int = 5):
        response = self.client.query_points(
            collection_name=collection_name,
            query=vector,
            limit=limit,
            with_payload=True,
        )
        return [
            RetrievedDocument(
                text=point.payload["text"],
                score=point.score,
                metadata=point.payload.get("metadata") or {},
            )
            for point in response.points
        ]
