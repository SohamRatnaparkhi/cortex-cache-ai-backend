from typing import Any, Dict, Optional

from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    query_id: str
    user_id: Optional[str] = ""
    conversation_id: str
    metadata: Optional[Dict[str, Any]] = None
    number: Optional[int] = None
    is_pro: Optional[bool] = False


class DBResponse(BaseModel):
    data: str
    memId: str
    chunk_id: str
    score: float
