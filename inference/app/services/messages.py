import asyncio
import logging
from typing import Dict, List, Optional
from uuid import uuid4

from prisma.models import Message, WebSearchCitations

from app.prisma.prisma import prisma

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)


async def insert_message_in_db(
    query_id: str,
    chunk_ids: List[str],
    memIds: List[str],
    user_id: str,
    conversation_id: str,
    user_query: str,
    content: str = "",
    only_message: bool = False,
    message_id: str = "",
    conversationFound: bool = True,
    web_citations: Optional[List[Dict[str, str]]] = None
) -> Message:
    """
    Insert or update message with related data in the database.

    Args:
        query_id: Unique identifier for the query
        chunk_ids: List of chunk IDs
        memIds: List of memory IDs
        user_id: User identifier
        conversation_id: Conversation identifier
        user_query: User's query text
        content: Message content
        only_message: Flag to update only message content
        message_id: Message identifier for updates
        conversationFound: Flag indicating if conversation exists
        web_citations: List of web citations [{"url": str, "title": str, "content": str, "source": str}]

    Returns:
        Message: Created or updated AI message

    Raises:
        ValueError: If database operations fail
    """
    try:
        async def create_web_citations(message_id: str, citations: List[Dict[str, str]]) -> List[WebSearchCitations]:
            """Create web citations for a message"""
            citation_data = [
                {
                    "id": str(uuid4()),
                    "url": citation["url"],
                    "title": citation["title"],
                    "content": citation["content"],
                    "source": citation["source"],
                    "messageId": message_id
                }
                for citation in citations
            ]

            # Create all citations in parallel
            print("Inserting web citations")
            return await asyncio.gather(*[
                prisma.websearchcitations.create(data=citation)
                for citation in citation_data
            ])

        # Handle message-only update
        if only_message:
            logger.info(f"Updating message content for ID: {message_id}")
            return await prisma.message.update(
                data={"content": content},
                where={"id": message_id},
            )

        # Create new conversation if needed
        if not conversationFound:
            logger.debug(f"Creating new conversation: {conversation_id}")
            print(f"Creating new conversation: {conversation_id}")
            conversation = await prisma.conversation.create({
                "id": conversation_id,
                "userId": user_id,
                "memoryIds": memIds,
            })
            # print(f"Conversation created: {conversation}")
            logger.debug(f"Conversation created: {conversation}")
            if not conversation:
                raise ValueError("Failed to create conversation")

        # Generate message IDs
        ai_message_id = str(uuid4())

        # Prepare messages data
        messages_data = {
            "ai_message": {
                "id": ai_message_id,
                "content": content,
                "sender": "ai",
                "conversationId": conversation_id,
                "chunkIds": chunk_ids,
                "memoryId": memIds,
                "questionId": query_id
            },
            "user_message": {
                "id": query_id,
                "content": user_query,
                "sender": user_id,
                "conversationId": conversation_id,
                "questionId": query_id,
                "chunkIds": chunk_ids,
                "memoryId": memIds
            }
        }

        # Execute database operations in a transaction
        async with prisma.batch_() as batcher:
            # Create AI message
            ai_db_message = await prisma.message.create(
                data=messages_data["ai_message"],
            )

            # Handle user message (update or create)
            user_db_message = await prisma.message.find_unique(
                where={"id": query_id},
            )

            if user_db_message:
                await prisma.message.update(
                    data={
                        "content": user_query,
                        "chunkIds": chunk_ids,
                        "memoryId": memIds,
                    },
                    where={"id": query_id}
                )
            else:
                await prisma.message.create(data=messages_data["user_message"])

            # Create web citations if provided
            if web_citations:
                await create_web_citations(ai_message_id, web_citations)

        if not ai_db_message:
            raise ValueError("Failed to create AI message")

        return ai_db_message

    except Exception as e:
        logger.error(f"Database operation failed: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to process message: {str(e)}")


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
