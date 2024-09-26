from typing import List

from prisma import Prisma

prisma = Prisma()


async def get_mem_based_on_id(memId: str):
    return await prisma.memory.find_many(where={"memId": memId})


async def get_all_mems_based_on_chunk_ids(chunk_ids: List[str]):
    return await prisma.memory.find_many(where={"chunkId": {"in": chunk_ids}})


async def get_mem_based_on_chunk_id(chunk_id: str):
    return await prisma.memory.find_unique(where={"chunkId": chunk_id})
