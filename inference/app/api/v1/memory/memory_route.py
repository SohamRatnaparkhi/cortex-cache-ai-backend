from fastapi import APIRouter, Request
from prisma.types import MemoryCreateInput, MemoryUpdateInput

from app.prisma.prisma import prisma
from app.schemas.query.ApiModel import QueryRequest
from app.services.Memory import get_final_results_from_memory
from app.services.MemoryOps import (CombinedMemory, CombinedMemoryChunk,
                                    get_all_memories_by_user_id,
                                    get_memory_by_id)
from app.utils.jwt import get_credentials
from app.utils.llms import pro_query_llm
from app.utils.prompts.MemorySearch import get_search_prompt

router = APIRouter(
    prefix='/memory',
    # tags=['memory']
)


@router.get('/memory/{memory_id}')
async def get_memory(memory_id: str):
    return await get_memory_by_id(memory_id)


@router.get('/all')
async def get_memories(request: Request):
    try:
        (userId, emailId, apiKey) = get_credentials(
            token=request.headers.get("Authorization"))

        if userId == "":
            return {"error": "Invalid JWT token"}

        memories = await get_all_memories_by_user_id(userId)
        return {
            "body": memories,
            "status": 200
        }
    except Exception as e:
        print(e)
        return {
            "error": "Invalid JWT token",
            "status": 400
        }


@router.patch('/memory/chunk-wise')
async def update_memory(memory: MemoryUpdateInput):
    return {"memory": memory}


@router.put('/memory/full')
async def update_memory_full(memory: MemoryCreateInput):
    return {"memory": memory}


@router.delete('/memory/{memory_id}')
async def delete_memory(memory_id: str):
    return {"memory_id": memory_id}


@router.post('/search')
async def search_memories(request: QueryRequest, request2: Request):
    try:
        header = request2.headers.get("Authorization")
        (userId, emailId, apiKey) = get_credentials(header)

        request.user_id = userId

        query = request.query
        prompt = get_search_prompt(query)

        improved_query = pro_query_llm.invoke(prompt)

        imp_q = ""
        if len(improved_query.content) > 17:
            imp_q = improved_query.content[17:]
        else:
            imp_q = improved_query.content

        combined_results = await get_final_results_from_memory(
            original_query=query, refined_query=imp_q, metadata=request.metadata, max_results=40, top_k=15)

        chunk_ids = [res['chunkId'] for res in combined_results]
        memIds = [res['memId'] for res in combined_results]

        unique_memIds = list(set(memIds))

        memories = await prisma.memory.find_many(where={"memId": {"in": unique_memIds}})
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

        return {
            "chunkIds": chunk_ids,
            "memIds": memIds,
            "body": combined_memories,
        }
    except Exception as e:
        print(e)
        return {"error": "Invalid JWT token"}
