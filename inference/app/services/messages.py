import logging
from uuid import uuid4

from prisma.models import Message

from app.prisma.prisma import prisma

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)


async def insert_message_in_db(query_id: str, chunk_ids: list[str], memIds: list[str], user_id: str, conversation_id: str, user_query: str, content: str = "", only_message: bool = False, message_id="", conversationFound=True) -> Message:
    """
    Insert the message after Pinecone search results.

    Args:
    query_id (str): The unique identifier for the query.
    chunk_ids (list[str]): The list of chunk IDs.
    memIds (list[str]): The list of memory IDs.
    user_id (str): The unique identifier for the user.
    conversation_id (str): The unique identifier for the conversation.
    """

    try:
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
                "memoryIds": memIds,
            })
            logger.info(f"Conversation created: {conversation}")
            if not conversation:
                raise ValueError("Conversation not created")

        # insert message
        logger.info("Inserting message in the database")
        ai_message = {
            "id": str(uuid4()),
            "content": content,
            "sender": "ai",
            "conversationId": conversation_id,
            "chunkIds": chunk_ids,
            "memoryId": memIds,
            "questionId": query_id
        }
        user_message = {
            "id": query_id,
            "content":  user_query,
            "sender":  user_id,
            "conversationId":  conversation_id,
            "questionId":  query_id,
            "chunkIds":  chunk_ids,
            "memoryId":  memIds
        }

        ai_db_message = await prisma.message.create(data=ai_message)
        user_db_message = await prisma.message.find_unique(where={"id": query_id})
        if user_db_message:
            logger.info("Updating existing message")
            user_db_message = await prisma.message.update(
                data={
                    "content": content,
                    "chunkIds": chunk_ids,
                    "memoryId": memIds,
                },
                where={
                    "id": query_id
                },
            )
        else:
            user_db_message = await prisma.message.create(data=user_message)

        if not ai_db_message:
            raise ValueError(" AI Message not created")

        if not user_db_message:
            raise ValueError("User Message not created")

        return ai_db_message
    except Exception as e:
        logger.error(f"Error inserting message in the database: {str(e)}")
        raise ValueError("Error inserting message in the database")


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
