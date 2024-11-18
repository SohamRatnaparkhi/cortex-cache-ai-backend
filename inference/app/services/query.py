from typing import AsyncIterator, Dict, List, Optional, Set

from langchain.schema import HumanMessage

from app.core import voyage_client
from app.prisma.prisma import prisma
from app.schemas.memory.ApiModel import Results
from app.schemas.query.query_related_types import (ChatContext, MessageContent,
                                                   QueryRequest)
from app.services.Memory import get_final_results_from_memory
from app.services.messages import insert_message_in_db
from app.utils.app_logger_config import logger
from app.utils.llms import get_answer_llm
from app.utils.Preprocessor import improve_query, preprocess_query
from app.utils.prompts.final_ans import prompt as final_ans_prompt
from app.utils.prompts.Pro_final_ans import (get_final_pro_answer,
                                             get_final_pro_answer_prompt)
from app.utils.prompts.query import generate_query_refinement_prompt


async def process_user_query(query: QueryRequest, is_stream: bool = False) -> Dict:
    """Process user query and return either stream response or final answer."""
    context, query_context, has_conversation = await get_chat_context(
        query.conversation_id,
        query.query_id,
        limit=2
    )

    refined_query = preprocess_query(query.query, context)
    prompt = generate_query_refinement_prompt(
        context=context,
        query=query.query,
        refined_query=refined_query,
        title=query.metadata.get("title", ""),
        description=query.metadata.get("description", "")
    )

    return await handle_query_response(
        query=query,
        context=context,
        query_context=query_context,
        is_stream=is_stream,
        refined_query=prompt,
        has_conversation=has_conversation
    )


async def handle_query_response(
    query: QueryRequest,
    context: str,
    query_context: str,
    is_stream: bool,
    refined_query: str,
    has_conversation: bool
) -> Dict:
    """Handle query processing and return appropriate response."""
    try:
        llm_query = improve_query(
            query.query, refined_query, query_context or context)
        logger.info(f"Improved query: {llm_query}")

        memory_results = []
        chunk_ids = []
        mem_ids = []

        if query.use_memory:
            memory_results = await get_final_results_from_memory(
                original_query=query.query,
                refined_query=llm_query,
                metadata=query.metadata,
                top_k=15
            )

            reranked_results = await voyage_client.re_rank_data(
                data=memory_results,
                k=10,
                query=llm_query
            )

            if not reranked_results:
                raise Exception("Failed to re-rank results")

            chunk_ids = [res.chunkId for res in reranked_results]
            mem_ids = [res.memId for res in reranked_results]
            memory_results = reranked_results

        message = await insert_message_in_db(
            query_id=query.query_id,
            chunk_ids=chunk_ids,
            memIds=mem_ids,
            user_id=query.user_id,
            conversation_id=query.conversation_id,
            user_query=query.query,
            conversationFound=has_conversation,
            content=query.query
        )

        if not query.use_memory:
            return handle_response_without_memory(query, llm_query, message.id, is_stream)

        memory_data = format_memory_xml(llm_query, memory_results)

        if is_stream:
            return {
                "curr_ans": memory_data,
                "query": llm_query,
                "prompt": get_pro_answer_prompt(query, llm_query, context, memory_data)
                if query.is_pro else final_ans_prompt + memory_data,
                "messageId": message.id
            }

        final_answer = get_final_pro_answer(
            query.query,
            llm_query,
            context,
            memory_data,
            llm=query.llm
        )

        return {
            "query": llm_query,
            "final_ans": final_answer.content,
            "messageId": message.id
        }

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return {"error": str(e)}


def format_memory_xml(query: str, results: List[Results]) -> str:
    """Format memory results in XML format."""
    data_entries = [
        f"<data>\n\t<content>{res.mem_data}</content>\n\t<data_score>{res.score}</data_score>\n</data>\n"
        for res in results
    ]
    return f"<question>{query}</question>\n{''.join(data_entries)}"


def handle_response_without_memory(query: QueryRequest, llm_query: str, message_id: str, is_stream: bool) -> Dict:
    """Handle response when memory is not used."""
    return {
        "curr_ans": "",
        "query": llm_query,
        "prompt": "",
        "messageId": message_id
    } if is_stream else {
        "query": llm_query,
        "final_ans": "",
        "messageId": message_id
    }


def get_pro_answer_prompt(query: QueryRequest, llm_query: str, context: str, memory_data: str) -> str:
    """Get prompt for pro users."""
    return get_final_pro_answer_prompt(
        original_query=query.query,
        refined_query=llm_query,
        context=context,
        initial_answer=memory_data,
        is_stream=True,
        use_memory=query.use_memory,
        agent=query.agent
    )


async def stream_response(
    prompt: str,
    message_id: str,
    llm_type: str = 'gpt-4o'
) -> AsyncIterator[str]:
    """
    Stream LLM responses and store the complete message.

    Args:
        prompt: The input prompt for the LLM
        message_id: Unique identifier for the message
        llm_type: Type of LLM to use
    """
    message_content = []
    first_chunk = True

    logger.debug(
        f"Starting stream with LLM type: {llm_type}, prompt: {prompt}")

    try:
        llm = get_answer_llm(llm_type, is_pro=True)
        async for chunk in llm.astream([HumanMessage(content=prompt)]):
            chunk_text = chunk.content
            message_content.append(chunk_text)

            # Format chunk for streaming
            chunk_data = chunk_text.replace('\n', '\\n')
            if first_chunk:
                yield f"messageId: {message_id},data: {chunk_data}\n\n"
                first_chunk = False
            else:
                yield f"data: {chunk_data}\n\n"

        # Store complete message
        complete_message = ''.join(message_content)
        logger.info(f"Complete message: {complete_message}")

        message = await insert_message_in_db(
            message_id=message_id,
            content=complete_message,
            only_message=True,
            chunk_ids=[],
            memIds=[],
            user_id="",
            user_query="",
            conversation_id="",
            query_id=""
        )

        if message:
            logger.info("Message stored successfully")

    except Exception as e:
        error_msg = f"Streaming error: {str(e)}"
        logger.error(error_msg)
        yield f"data: {error_msg}\n\n"


async def get_chat_context(
    conversation_id: str,
    query_id: Optional[str] = None,
    limit: int = 2
) -> ChatContext:
    """
    Retrieve and format chat context from previous messages.

    Args:
        conversation_id: ID of the conversation
        query_id: Optional ID of current query to exclude
        limit: Maximum number of previous messages to include
    """
    try:
        messages = await prisma.message.find_many(
            where={"conversationId": conversation_id},
            order={"createdAt": "desc"}
        )

        if not messages:
            return ChatContext(context="", query_context="", has_conversation=False)

        # Collect relevant query IDs
        query_ids: Set[str] = set()
        for msg in messages:
            if msg.sender != "ai" and msg.id != query_id:
                query_ids.add(msg.id)
                if len(query_ids) == limit:
                    break

        if not query_ids:
            return ChatContext(context="", query_context="", has_conversation=True)

        # Build context dictionary
        context_map: Dict[str, MessageContent] = {}
        for msg in messages:
            if msg.id in query_ids:
                context_map[msg.id] = MessageContent(user=msg.content)
            elif msg.questionId in query_ids:
                if msg.questionId not in context_map:
                    context_map[msg.questionId] = MessageContent(user="")
                context_map[msg.questionId].ai = msg.content[:300]

        # Format contexts
        query_context = ", ".join(
            ctx.user for ctx in context_map.values()
        )

        full_context = "\n".join(
            f"User: {ctx.user}\nAI: {ctx.ai or ''}"
            for ctx in context_map.values()
        )

        return ChatContext(
            context=full_context,
            query_context=query_context,
            has_conversation=True
        )

    except Exception as e:
        logger.error(f"Error fetching chat context: {str(e)}")
        return ChatContext(context="", query_context="", has_conversation=bool(messages))
