from typing import List

from pydantic import BaseModel

from app.schemas.Metadata import Metadata


class AgentResponse(BaseModel):
    transcript: str
    chunks: List[str]
    metadata: List[Metadata]

class AgentError(BaseModel):
    error: str

class AgentResponseWrapper(BaseModel):
    response: AgentResponse | None = None
    error: AgentError | None = None
