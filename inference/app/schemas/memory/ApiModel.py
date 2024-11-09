from typing import List, Optional

from prisma.models import Memory, MindMap
from prisma.models import User as UserModel
from pydantic import BaseModel


class UpdateMemory(BaseModel):
    memoryId: str
    memData: str


class MemoryGroup(BaseModel):
    chunkId: str
    memData: str


class GetMemoryOutput(BaseModel):
    memories: list[MemoryGroup]
    memoryId: str
    title: str
    memType: str
    memData: str
    source: Optional[str] = None
    tags: List[str]
    metadata: Optional[dict] = None
    createdAt: str
    updatedAt: str
    mindMapId: Optional[str] = None
    userId: str
    mindMap: Optional[MindMap] = None
    User: Optional[UserModel] = None


class Results(BaseModel):
    memId: str
    chunkId: str
    mem_data: str


class ResultsAfterReRanking(Results):
    score: float
