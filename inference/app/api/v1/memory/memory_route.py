from fastapi import APIRouter, Request
from prisma.types import MemoryCreateInput, MemoryUpdateInput

from app.prisma.prisma import prisma
from app.services.MemoryOps import (get_all_memories_by_user_id,
                                    get_memory_by_id)
from app.utils.jwt import get_credentials

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
