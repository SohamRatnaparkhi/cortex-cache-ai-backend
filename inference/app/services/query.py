import asyncio
import json
import re
import time
from typing import AsyncIterator, Dict, List

from langchain.schema import HumanMessage

from app.core import voyage_client
from app.prisma.prisma import get_all_mems_based_on_chunk_ids, prisma
from app.schemas.memory.ApiModel import Results
from app.schemas.query.ApiModel import QueryRequest
from app.services.Memory import get_final_results_from_memory
from app.services.messages import insert_message_in_db
from app.utils.app_logger_config import logger
from app.utils.llms import get_answer_llm
from app.utils.Preprocessor import improve_query, preprocess_query
from app.utils.prompts.final_ans import prompt as final_ans_prompt
from app.utils.prompts.Pro_final_ans import (get_final_pro_answer,
                                             get_final_pro_answer_prompt)
from app.utils.prompts.query import generate_query_refinement_prompt
from app.utils.prompts.ResponseScoring import scoring_prompt


async def user_query_service(query: QueryRequest, is_stream=False):

    message = query.query

    metadata = query.metadata

    title = metadata.get("title", "")
    description = metadata.get("description", "")

    context, query_only_context, conversationFound = await get_chat_context(query.conversation_id, query.query_id, limit=2)

    print("Context: ", context)

    updated_query = preprocess_query(message, context)
    prompt = generate_query_refinement_prompt(
        context=context, query=message, refined_query=updated_query, title=title, description=description)
    return await process_single_query(query, context, is_stream, newQuery=prompt, conversationFound=conversationFound)


async def process_single_query(query: QueryRequest, context: str, is_stream=False, newQuery="", conversationFound=False, query_only_context: str = "") -> Dict:
    try:
        start_time = time.time()
        message = query.query
        metadata = query.metadata
        refined_query = newQuery
        is_pro = query.is_pro

        use_memory = query.use_memory

        logger.debug(
            f"Improving LLM query with message: '{message}' and refined_query: '{refined_query}'")

        query_context = query_only_context if query_only_context else context

        llm_query = improve_query(message, refined_query, query_context)
        logger.info(f"Improved LLM query: {llm_query}")
        logger.debug(
            f"Improve query time: {time.time() - start_time:.4f} seconds")

        combined_results = None
        chunk_ids = []
        mem_ids = []
        if use_memory:
            pinecone_start = time.time()
            combined_results: List[Results] = await get_final_results_from_memory(
                original_query=message,
                refined_query=llm_query,
                metadata=metadata,
                top_k=15
            )
            logger.debug(
                f"Pinecone query time: {time.time() - pinecone_start:.4f} seconds")

            re_ranked_results = await voyage_client.re_rank_data(
                data=combined_results,
                k=10,
                query=llm_query
            )

            if re_ranked_results is None:
                raise Exception("Error re-ranking data")

            chunk_ids = [res.chunkId for res in re_ranked_results]
            mem_ids = [res.memId for res in re_ranked_results]

        logger.info("Inserting message into the database")
        message = await insert_message_in_db(
            query_id=query.query_id,
            chunk_ids=chunk_ids,
            memIds=mem_ids,
            user_id=query.user_id,
            conversation_id=query.conversation_id,
            user_query=query.query,
            conversationFound=conversationFound,
            content=message
        )
        logger.info("Message inserted into the database")

        complete_data = ""
        if use_memory:
            complete_data_start = time.time()

            ans_list = []

            data_entries = []
            for i in range(len(re_ranked_results)):
                res = re_ranked_results[i]

                current_ans = {
                    "chunk_id": res.chunkId,
                    "score": res.score,
                    "mem_data": res.mem_data,
                    "memId": res.memId
                }
                data_entries.append(
                    f"<data>\n\t<content>{current_ans['mem_data']}</content>\n\t<data_score>{current_ans['score']}</data_score>\n</data>\n"
                )
                ans_list.append(current_ans)

            complete_data = f"<question>{llm_query}</question>\n{''.join(data_entries)}"
            logger.debug(
                f"Build complete data time: {time.time() - complete_data_start:.4f} seconds")
            logger.info(f"Message: {message}")

        final_ans_start = time.time()

        if is_pro:
            if is_stream:
                return {
                    "curr_ans": complete_data,
                    "query": llm_query,
                    "prompt": get_final_pro_answer_prompt(
                        original_query=query.query,
                        refined_query=llm_query,
                        context=context,
                        initial_answer=complete_data,
                        is_stream=True,
                        use_memory=query.use_memory,
                        agent=query.agent
                    ),
                    "messageId": message.id
                }
            final_ans = get_final_pro_answer(
                message, refined_query, context, complete_data, llm=query.llm)
        else:
            if is_stream:
                return {
                    "curr_ans": complete_data,
                    "query": llm_query,
                    "prompt": final_ans_prompt + complete_data,
                    "messageId": message.id
                }
            final_ans = get_final_answer(complete_data)

        logger.debug(
            f"Get final answer time: {time.time() - final_ans_start:.4f} seconds")
        logger.debug(
            f"Total process_single_query time: {time.time() - start_time:.4f} seconds")

        result = {
            "query": llm_query,
            "final_ans": convert_newlines(final_ans.content),
            "messageId": message.id
        }
        return result

    except Exception as e:
        logger.error(f"Error in process_single_query: {str(e)}")
        return {"error": str(e)}


async def user_multi_query_service2(query: QueryRequest):
    start_time = time.time()

    message = query.query
    metadata = query.metadata
    context, query_only_context,  = get_chat_context(query.conversation_id)

    updated_query = preprocess_query(message, context)
    refined_queries = generate_query_refinement_prompt(
        context=context, query=message, refined_query=updated_query)
    # parallel execution of queries
    results = await asyncio.gather(*[process_single_query(query, context, False, refined_queries) for refined_query in refined_queries])
    all_res_time = time.time() - start_time
    logger.info(f"All results time: {all_res_time:.4f} seconds")

    score_start = time.time()
    scored_answers = score_answers(message, updated_query, context, results[0]["final_ans"], results[
                                   1]["final_ans"], results[2]["final_ans"], results[3]["final_ans"], results[4]["final_ans"])
    logger.info(f"Score answers time: {time.time() - score_start:.4f} seconds")
    logger.info(
        f"Total user_multi_query_service2 time: {time.time() - start_time:.4f} seconds")
    return {
        "scored_answers": scored_answers,
        "final_ans": results
    }


def get_final_answer(curr_ans):
    prompt = final_ans_prompt
    final_ans = llm.invoke(prompt + curr_ans)
    return final_ans


def score_answers(original_query, refined_query, context, answer1, answer2, answer3, answer4, answer5):
    prompt = scoring_prompt(original_query, refined_query,
                            context, answer1, answer2, answer3, answer4, answer5)
    scored_answers = llm.invoke(prompt)
    return scored_answers


async def stream_response(prompt: str, messageId: str, llm_type: str = 'gpt-4o') -> AsyncIterator[str]:
    # "got the prompt"
    message_content = ""
    message_id_sent = False
    print(f"LLM type: {llm_type}")
    llm = get_answer_llm(llm_type, is_pro=True)
    logger.debug(f"Streaming response with prompt: {prompt}")
    try:
        async for chunk in llm.astream([HumanMessage(content=prompt)]):
            # print(chunk.content, end="")

            if not message_id_sent:
                message_id_sent = True
                message_content += chunk.content
                chunk_content = chunk.content.replace('\n', '\\n')
                yield f"messageId: {messageId},data: {chunk_content}\n\n"
                continue
            message_content += chunk.content
            chunk_content = chunk.content.replace('\n', '\\n')
            yield f"data: {chunk_content}\n\n"
        logger.info(message_content)
        # Store message in the conversation in the database
        message = await insert_message_in_db(query_id="", chunk_ids=[], memIds=[], user_id="", user_query="", content=message_content, only_message=True, message_id=messageId, conversation_id="")
        if message is not None:
            logger.info("Message inserted in db")
    except Exception as e:
        logger.info(f"Error during streaming: {str(e)}")
        yield f"data: Error occurred during streaming: {str(e)}\n\n"


def preprocess_json_string(json_string):
    # Remove newline characters within the JSON string values
    json_string = re.sub(r'(?<!\\)\\n', ' ', json_string)
    # Replace double backslashes with single backslashes
    json_string = json_string.replace('\\\\', '\\')
    return json_string


def parse_response(response_string):
    try:
        # Parse the outer JSON structure
        response_dict = json.loads(response_string)

        # Get the 'final_ans' string and preprocess it
        final_ans_string = preprocess_json_string(response_dict['final_ans'])

        # Parse the preprocessed 'final_ans' string
        final_ans_dict = json.loads(final_ans_string)

        return final_ans_dict
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return response_string


def convert_newlines(text):
    # Replace single \n with two spaces and a newline
    converted = re.sub(r'([^\n])\n(?!\n)', r'\1  \n', text)
    # Replace double \n with double newline (paraph break)
    converted = re.sub(r'\n\n', '\n\n', converted)
    return converted


async def get_chat_context(conversation_id: str, query_id: str | None = None, limit=2):
    try:
        messages = await prisma.message.find_many(
            where={
                "conversationId": conversation_id
            },
            order={
                "createdAt": "desc"
            })
        queryIds = set()
        # print(messages)
        for message in messages:
            if message.sender != "ai":
                if query_id != None and message.id == query_id:
                    continue
                queryIds.add(message.id)
            if len(queryIds) == limit:
                break
        if len(queryIds) == 0:
            return "", "", len(messages) > 0
        context = {}
        for message in messages:
            if message.id in queryIds:
                context[message.id] = {
                    "user": message.content
                }
            if message.questionId in queryIds:
                if (message.questionId not in context):
                    context[message.questionId] = {}
                context[message.questionId]["ai"] = message.content[0: 300]

        query_only_context = ""
        for key in context.keys():
            query_only_context = f"{context[key]['user']}, " + \
                query_only_context

        final_context = ""
        for key in context.keys():
            final_context += f"User: {context[key]['user']}\nAI: {context[key]['ai']}\n"

        return final_context, query_only_context, len(messages) > 0

    except Exception as e:
        print(f"Error in get_chat_context: {str(e)}")
        return "", "", len(messages) > 0
