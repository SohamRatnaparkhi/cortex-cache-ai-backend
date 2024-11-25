from typing import List, Literal, TypedDict, Union

from prisma.models import Memory

from app.prisma.prisma import prisma
from app.services.query import get_chat_context
from app.utils.app_logger_config import logger
from app.utils.llms import summary_llm


class MemoryCitation(TypedDict):
    id: str
    content: str
    type: Literal['memory']
    memType: str
    title: str
    chunkId: str
    metadata: dict


class WebCitation(TypedDict):
    id: str
    url: str
    title: str
    content: str
    type: Literal['web']
    source: str


class CitationsResponse(TypedDict):
    citations: List[Union[MemoryCitation, WebCitation]]
    memoryIds: List[str]
    chunkIds: List[str]


async def get_citations_on_message_id(
    message_id: str,
    title: str,
    conversation_id: str
) -> CitationsResponse:
    """
    Get both memory and web citations for a message.

    Args:
        message_id: Unique identifier for the message
        title: Title to update in the conversation
        conversation_id: Conversation identifier

    Returns:
        CitationsResponse containing combined citations and IDs

    Raises:
        ValueError: If message not found or other errors occur
    """
    try:
        # Get message with web citations
        message = await prisma.message.find_unique(
            where={"id": message_id},
        )

        # print(f"Web citations: {message.WebSearchCitations}")
        web_citations = await prisma.websearchcitations.find_many(
            where={"messageId": message_id}
        )

        if not message:
            raise ValueError(f"Message not found: {message_id}")

        # Extract IDs
        chunk_ids = list(sorted(set(message.chunkIds))
                         ) if message.chunkIds else []
        memory_ids = message.memoryId if message.memoryId else []

        # Fetch memory citations
        memory_citations: List[Memory] = await prisma.memory.find_many(
            where={"chunkId": {"in": chunk_ids}}
        )

        # Format memory citations
        formatted_memory_citations: List[MemoryCitation] = [
            {
                "id": str(memory.memId),
                "content": memory.memData,
                "title": memory.title,
                "memType": memory.memType,
                "type": "memory",
                "chunkId": memory.chunkId,
                "metadata": memory.metadata if hasattr(memory, 'metadata') else {}
            }
            for memory in memory_citations
        ]

        # Format web citations
        formatted_web_citations: List[WebCitation] = [
            {
                "id": citation.id,
                "url": citation.url,
                "title": citation.title,
                "content": citation.content,
                "type": "web",
                "source": citation.source
            }
            for citation in (web_citations or [])
        ]

        # Combine all citations
        all_citations = formatted_memory_citations + formatted_web_citations

        # Update conversation title asynchronously
        try:
            logger.info(
                f"Updating conversation {conversation_id} with title: {title}")
            await prisma.conversation.update(
                where={"id": conversation_id},
                data={"title": title}
            )
        except Exception as e:
            logger.error(f"Failed to update conversation title: {str(e)}")
            # Continue execution even if title update fails

        return {
            "citations": all_citations,
            "memoryIds": memory_ids,
            "chunkIds": chunk_ids
        }

    except Exception as e:
        logger.error(f"Error retrieving citations: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to get citations: {str(e)}")


async def get_convo_summary(conversation_id: str):
    try:
        context = await get_chat_context(conversation_id, limit=3)
        print(f"Context: {context}")
        res = summary_llm.invoke(context.context)
        await prisma.conversation.update(
            where={"id": conversation_id},
            data={"summary": res.content}
        )
        print(f"Summary: {res.content}")
        return {
            "summary": res.content
        }
    except Exception as e:
        print(f"Error in get_convo_summary: {str(e)}")
        return "Error in get_convo_summary"
