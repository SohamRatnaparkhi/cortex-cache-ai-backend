from app.prisma.prisma import prisma


async def get_citations_on_message_id(message_id: str):
    """
    Get the citations for a message.

    Args:
    message_id (str): The unique identifier for the message.

    Returns:
    citations (list[str]): The list of citations.
    """
    try:
        message = await prisma.message.find_unique(where={"id": message_id})
        if not message:
            raise ValueError("Message not found")
        [chunkIds, ] = message.chunkIds,
        memoryIds = message.memoryId
        print(chunkIds)
        # chunk_memory_map = {}

        # for chunkId in chunkIds:
        #     mem_id_of_chunk = "_".split(chunkId)[0]
        #     if mem_id_of_chunk not in chunk_memory_map:
        #         chunk_memory_map[mem_id_of_chunk] = []
        #     chunk_memory_map[mem_id_of_chunk].append(chunkId)

        specific_memories = await prisma.memory.find_many(where={
            "chunkId": {
                "in": list(sorted(set(chunkIds)))
            }
        })
        return {
            "citations": specific_memories,
            "memoryIds": memoryIds,
            "chunkIds": chunkIds
        }
    except Exception as e:
        raise ValueError(f"Error getting citations for message: {e}")
