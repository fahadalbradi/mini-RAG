from .BaseDataModel import BaseDataModel
from .db_schemes import DataChunk
from .enums.DataBaseEnum import DataBaseEnum
from bson.objectid import ObjectId
from pymongo import InsertOne

class ChunkModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_CHUNK_NAME.value]

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        await instance.init_indexes(instance.collection, DataChunk.get_indexes())
        return instance

    async def insert_many_chunks(self, chunks: list, batch_size: int = 100):
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            operations = [
                InsertOne(chunk.model_dump(by_alias=True, exclude_none=True))
                for chunk in batch
            ]
            await self.collection.bulk_write(operations)
        return len(chunks)

    async def delete_chunks_by_project_id(self, project_id: ObjectId):
        result = await self.collection.delete_many({"chunk_project_id": project_id})
        return result.deleted_count

    async def get_project_chunks(self, project_id: ObjectId, page_no: int = 1, page_size: int = 50):
        cursor = self.collection.find({"chunk_project_id": project_id}) \
                                .sort("_id", 1) \
                                .skip((page_no - 1) * page_size) \
                                .limit(page_size)
        return [DataChunk(**record) async for record in cursor]

    async def count_project_chunks(self, project_id: ObjectId):
        return await self.collection.count_documents({"chunk_project_id": project_id})
