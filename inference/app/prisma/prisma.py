from typing import List

from prisma import Prisma

prisma = Prisma()


async def get_mem_based_on_id(memId: str):
    return await prisma.memory.find_many(where={"memId": memId})


async def get_all_mems_based_on_chunk_ids(chunk_ids: List[str]):
    return await prisma.memory.find_many(where={"chunkId": {"in": chunk_ids}})


async def get_mem_based_on_chunk_id(chunk_id: str):
    return await prisma.memory.find_unique(where={"chunkId": chunk_id})


async def full_text_search(query: str, metadata: dict, top_k: int = 10):
    try:
        filters = {}
        for key, value in metadata.items():
            if (key == 'user_id'):
                key = 'userId'
            if (key == 'mem_id'):
                key = 'memId'
            if isinstance(value, str):
                filters[key] = value
            elif isinstance(value, list):
                filters = {key: {"in": value}}
            else:
                continue

        filter_string = ""

        for key in filters.keys():
            filter_string += f'AND m."{key}" = \'{filters[key]}\' '

        search_query = f"""
        SELECT m."memId", m."chunkId", m."memData", ts_rank(msv.search_vector, plainto_tsquery('english', '{query}')) AS score
        FROM "Memory" m
        JOIN memory_search_vector msv ON m."memId" = msv."memid" AND m."chunkId" = msv."chunkid"
        WHERE msv.search_vector @@ plainto_tsquery('english', '{query}') {filter_string}
        ORDER BY score DESC
        LIMIT {top_k}
        """
        results = await prisma.query_raw(search_query)
        # print("_____------------_____")
        # print(results)
        # print("_____------------_____")
    except Exception as e:
        print(f"Error performing full-text search: {str(e)}")
        results = []
    return results
