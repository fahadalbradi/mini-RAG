from pydantic import BaseModel, Field, validator
from typing import Optional
from bson.objectid import objectId

class Project(BaseModel):
    _id: Optional[objectId]
    chunk_text: str = Field(..., min_length=1)
    chunk_metadata: dict
    chunk_order: int = Field(..., gt=0)
    chunk_project_id: objectId

    class Config:
        arbitrary_types_allowed = True


