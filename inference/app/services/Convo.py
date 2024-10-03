from app.prisma.prisma import prisma
from app.services.query import get_chat_context
from app.utils.llms import summary_llm


async def get_citations_on_message_id(message_id: str, title: str, conversation_id: str):
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

        specific_memories = await prisma.memory.find_many(where={
            "chunkId": {
                "in": list(sorted(set(chunkIds)))
            }
        })

        try:
            await prisma.conversation.update(
                where={"id": conversation_id},
                data={"title": title}
            )
        except Exception as e:
            print(f"Error updating conversation title: {e}")
        return {
            "citations": specific_memories,
            "memoryIds": memoryIds,
            "chunkIds": chunkIds
        }
    except Exception as e:
        raise ValueError(f"Error getting citations for message: {e}")


async def get_convo_summary(conversation_id: str):
    try:
        context = await get_chat_context(conversation_id, limit=3)
        print(f"Context: {context}")
        res = summary_llm.invoke(context[0])
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
