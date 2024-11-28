import json
import os

import asyncpg
from dotenv import load_dotenv
from prisma.models import Memory

from app.prisma.prisma import prisma


def sanitize_input(data):
    # Replace NUL characters
    sanitized_data = {key: value.replace(
        '\x00', '') for key, value in data.items()}
    return sanitized_data


async def insert_memory_to_db(memory_data: dict):
    # sanitized_data = sanitize_input(memory_data)
    # print(f"Sanitized data: {sanitized_data}")
    memory = await prisma.memory.create(data=memory_data)
    return memory


async def insert_many_memories_to_db(memory_data: list, isCode=False, preprocessed_chunks=[]):
    # memory_data = [sanitize_input(memory) for memory in memory_data]
    try:
        memories = await prisma.memory.create_many(data=memory_data)
        memory_ids = []
        chunk_ids = []
        filtered_meta_data = []
        JOINER = '<joiner>'
        CENTRAL_OPENER = '<central>'
        CENTRAL_CLOSER = '</central>'
        if isCode:
            JOINER = ' '
            CENTRAL_OPENER = ''
            CENTRAL_CLOSER = ''
        data = []

        i = 0
        for i in range(len(memory_data)):
            if (i < len(preprocessed_chunks)):
                data.append({
                    "memId": memory_data[i]["memId"],
                    "chunkId": memory_data[i]["chunkId"],
                    "memData": preprocessed_chunks[i]
                })
            else:
                data.append({
                    "memId": memory_data[i]["memId"],
                    "chunkId": memory_data[i]["chunkId"],
                    "memData": memory_data[i]["memData"]
                })

        for memory in data:
            memory_ids.append(memory["memId"])
            chunk_ids.append(memory["chunkId"])
            filteredMemory = memory["memData"].replace(
                CENTRAL_OPENER, "").replace(CENTRAL_CLOSER, "").replace(JOINER, "")
            filtered_meta_data.append(filteredMemory)

        await update_search_vectors(memory_ids, chunk_ids, filtered_meta_data)
        return memories
    except Exception as e:
        print(f"Error inserting many memories: {e}")
        return -1

if os.path.exists('.env'):
    load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')


async def update_search_vectors(mem_ids, chunk_ids, mem_data):
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        # Prepare the data for bulk insert
        values = list(zip(mem_ids, chunk_ids, mem_data))
        print(f"Inserting {len(values)} search vectors in connection {conn}")
        # Perform bulk upsert
        await conn.executemany('''
            INSERT INTO memory_search_vector (memId, chunkId, search_vector)
            VALUES ($1, $2, to_tsvector('english', $3))
            ON CONFLICT (memId, chunkId) DO UPDATE
            SET search_vector = to_tsvector('english', $3)
        ''', values)

    except Exception as e:
        print(f"Error updating search vectors: {e}")
    finally:
        await conn.close()
