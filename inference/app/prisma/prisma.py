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
        # First normalize the keys
        for key, value in metadata.items():
            if key == 'user_id':
                key = 'userId'
            if key == 'mem_id':
                key = 'memId'

            if isinstance(value, str):
                filters[key] = {"equals": value}
            elif isinstance(value, list):
                if value:  # Only add if list is not empty
                    filters[key] = {"in": value}

        # Build the filter string with proper handling of both single values and arrays
        filter_conditions = []
        for key, condition in filters.items():
            if "equals" in condition:
                # For single string values
                filter_conditions.append(
                    f'm."{key}" = \'{condition["equals"]}\'')
            elif "in" in condition:
                # For array values - use ANY or = ANY syntax
                placeholders = ', '.join(
                    f"'{str(x)}'" for x in condition["in"])
                filter_conditions.append(
                    f'm."{key}" = ANY(ARRAY[{placeholders}])')
        # Combine all conditions with AND
        filter_string = " AND " + \
            " AND ".join(filter_conditions) if filter_conditions else ""

        search_query = f"""
            SELECT m."memId", m."chunkId", m."memData", ts_rank(msv.search_vector, plainto_tsquery('english', '{query}')) AS score
            FROM "Memory" m
            JOIN memory_search_vector msv ON m."memId" = msv."memid" AND m."chunkId" = msv."chunkid"
            WHERE msv.search_vector @@ plainto_tsquery('english', '{query}') {filter_string}
            ORDER BY score DESC
            LIMIT {top_k};
        """
        results = await prisma.query_raw(search_query)
        # print("_____------------_____")
        # print(results)
        # print("_____------------_____")
    except Exception as e:
        print(f"Error performing full-text search: {str(e)}")
        results = []
    return results
