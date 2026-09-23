from pydantic import BaseModel
from typing import Optional

class ProcessRequest(BaseModel):
    # Omit file_id to process every file uploaded to the project
    file_id: Optional[str] = None
    chunk_size: Optional[int] = 800
    overlap: Optional[int] = 100
    do_reset: Optional[int] = 0
