from typing import Any, Dict, Optional

from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    metadata: Optional[Dict[str, Any]] = None

class DBResponse(BaseModel):
    data: str
    mem_id: str
    chunk_id: str
    score: float