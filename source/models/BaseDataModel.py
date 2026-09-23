from helpers.config import get_settings

class BaseDataModel:

    def __init__(self, db_client: object):
        self.db_client = db_client
        self.app_settings = get_settings()

    async def init_indexes(self, collection, indexes: list):
        for index in indexes:
            await collection.create_index(
                index["key"],
                name=index["name"],
                unique=index["unique"],
            )
