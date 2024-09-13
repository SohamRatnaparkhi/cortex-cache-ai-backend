from prisma.models import Memory

from app.prisma.prisma import prisma


async def insert_memory_to_db(memory_data: dict):
    memory = await prisma.memory.create(data=memory_data)
    return memory

async def insert_many_memories_to_db(memory_data: list):
    memories = await prisma.memory.create_many(data=memory_data)
    return memories