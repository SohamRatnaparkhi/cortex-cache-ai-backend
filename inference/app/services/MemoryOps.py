from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.core.PineconeClient import PineconeClient
from app.prisma.prisma import prisma
from app.schemas.memory.ApiModel import GetMemoryOutput, MemoryGroup

client = PineconeClient()


async def get_memory_by_id(memory_id: str) -> GetMemoryOutput:
    memories = await prisma.memory.find_many(where={"id": memory_id})

    if memories is None:
        raise ValueError("Memory not found")

    groups = [MemoryGroup(chunkId=mem.chunkId, memData=mem.memData)
              for mem in memories]
    res = GetMemoryOutput(
        memories=groups,
        memoryId=memories[0].id,
        title=memories[0].title,
        memType=memories[0].memType,
        memData=memories[0].memData,
        tags=memories[0].tags,
        createdAt=memories[0].createdAt,
        updatedAt=memories[0].updatedAt,
        userId=memories[0].userId
    )
    return res


class CombinedMemoryChunk(BaseModel):
    chunk_id: str
    contents: str


class CombinedMemory(BaseModel):
    chunks: List[CombinedMemoryChunk]
    metadata: Dict[str, Any]
    mem_id: str
    mem_type: str
    user_id: str
    created_at: Any
    updated_at: Any
    tags: Optional[List[str]] = None


async def get_all_memories_by_user_id(userId: str) -> Dict[str, CombinedMemory]:
    memories = await prisma.memory.find_many(where={"userId": userId})
    combined_memories = {}

    for memory in memories:
        mem_id = memory.memId

        if mem_id not in combined_memories:
            combined_memories[mem_id] = CombinedMemory(
                chunks=[],
                metadata=memory.metadata,
                mem_id=mem_id,
                mem_type=memory.memType,
                user_id=memory.userId,
                created_at=memory.createdAt,
                updated_at=memory.updatedAt,
                tags=memory.tags
            )

        combined_memories[mem_id].chunks.append(CombinedMemoryChunk(
            chunk_id=memory.chunkId,
            contents=memory.memData
        ))

    for mem in combined_memories.values():
        mem.chunks.sort(key=lambda x: int(x.chunk_id.split('_')[-1]))

    return combined_memories


async def update_memory_chunk_wise(memory_id: str, memData: str):
    memory = await prisma.memory.find_unique(where={"id": memory_id})
    if memory is None:
        raise ValueError("Memory not found")
    updated = await prisma.memory.update(
        where={"id": memory_id},
        data={"memData": memData}
    )

    # update in pinecone
    pinecone_chunk_id = memory_id + "_" + memory.chunkId
    metadata = updated.metadata
    client.update(id=pinecone_chunk_id, data=memData, metadata=metadata)

    return {"memory_id": memory_id}
