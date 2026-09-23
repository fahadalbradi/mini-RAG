from .BaseDataModel import BaseDataModel
from .db_schemes import Asset
from .enums.DataBaseEnum import DataBaseEnum
from bson.objectid import ObjectId

class AssetModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_ASSET_NAME.value]

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        await instance.init_indexes(instance.collection, Asset.get_indexes())
        return instance

    async def create_asset(self, asset: Asset):
        result = await self.collection.insert_one(asset.model_dump(by_alias=True, exclude_none=True))
        asset.id = result.inserted_id
        return asset

    async def get_all_project_assets(self, asset_project_id: ObjectId, asset_type: str):
        cursor = self.collection.find({
            "asset_project_id": asset_project_id,
            "asset_type": asset_type,
        }).sort("asset_pushed_at", 1)
        return [Asset(**record) async for record in cursor]

    async def get_asset_record(self, asset_project_id: ObjectId, asset_name: str):
        record = await self.collection.find_one({
            "asset_project_id": asset_project_id,
            "asset_name": asset_name,
        })
        return Asset(**record) if record else None
