from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    query_id: str
    llm: str
    user_id: Optional[str] = ""
    conversation_id: Optional[str] = ""
    metadata: Optional[Dict[str, Any]] = None
    is_pro: Optional[bool] = False
    agent: Optional[str] = "default"
    use_memory: Optional[bool] = True
    use_web: Optional[bool] = False
    web_sources: Optional[List[str]] = []


class MemoryQueryRequest(BaseModel):
    query: str
    metadata: Optional[Dict[str, Any]] = None


class DBResponse(BaseModel):
    data: str
    memId: str
    chunk_id: str
    score: float


class ChatContext(BaseModel):
    context: str
    query_context: str
    has_conversation: bool


class MessageContent(BaseModel):
    user: str
    ai: Optional[str] = None
