import logging

from prisma.models import Message

from app.prisma.prisma import prisma

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)



async def insert_message_in_db(query_id: str, chunk_ids: list[str], mem_ids: list[str], user_id: str, conversation_id: str, user_query: str, content: str = "", only_message: bool = False, message_id = "", conversationFound = True) -> Message:
    """
    Insert the message after Pinecone search results.
    
    Args:
    query_id (str): The unique identifier for the query.
    chunk_ids (list[str]): The list of chunk IDs.
    mem_ids (list[str]): The list of memory IDs.
    user_id (str): The unique identifier for the user.
    conversation_id (str): The unique identifier for the conversation.
    """

    
    if only_message:
        logger.info("Updating message in the database")
        return await prisma.message.update(
            data={
                "content": content
            },
            where={
                "id": message_id
            },
        )
    # check if conversation exists
    # conversation = None
    if not conversationFound:
        conversation = await prisma.conversation.create({
            "id": conversation_id,
            "userId": user_id,
            "memoryIds": mem_ids,
        })
        logger.info(f"Conversation created: {conversation}")
        if not conversation:
            raise ValueError("Conversation not created")
    
    # insert message
    logger.info("Inserting message in the database")
    ai_message = {
        "content": content,
        "sender": "ai",
        "conversationId": conversation_id,
        "chunkIds": chunk_ids,
        "memoryId": mem_ids,
        "questionId": query_id
    }
    user_message = {
        "id": query_id,
        "content":  user_query,
        "sender":  user_id,
        "conversationId":  conversation_id,
        "questionId":  query_id,
        "chunkIds":  chunk_ids,
        "memoryId":  mem_ids
    }
    ai_db_message = await prisma.message.create(data=ai_message)
    user_db_message = await prisma.message.create(data=user_message)
    # total = await prisma.message.create_many([ai_message, user_message])

    if not ai_db_message:
        raise ValueError(" AI Message not created")
    
    if not user_db_message:
        raise ValueError("User Message not created")
    
    logger.info(f"AI message inserted: {ai_db_message}")
    return ai_db_message

def get_chunks_and_message_from_db(message_id: str) -> dict:
    """
    Get the chunk IDs and message content from the database.
    
    Args:
    message_id (str): The unique identifier for the message.
    """
    message = prisma.message.find_unique(where={"id": message_id})
    if not message:
        raise ValueError("Message not found")
    
    return {
        "chunk_ids": message.chunkIds,
        "message": message.content
    }