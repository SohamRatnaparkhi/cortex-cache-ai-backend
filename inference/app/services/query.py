import asyncio
import json
import logging
import re
import time
from typing import AsyncIterator, Dict

from langchain.schema import HumanMessage

from app.prisma import prisma as prisma_mod
from app.prisma.prisma import get_all_mems_based_on_chunk_ids, prisma
from app.schemas.query.ApiModel import QueryRequest
from app.services.Memory import get_final_results_from_memory
from app.services.messages import insert_message_in_db
from app.utils.llms import answer_llm_pro as llm
from app.utils.Pinecone_query import pinecone_query
from app.utils.Preprocessor import (improve_query, prepare_fulltext_query,
                                    preprocess_query)
from app.utils.prompts.final_ans import prompt as final_ans_prompt
from app.utils.prompts.Pro_final_ans import (get_final_pro_answer,
                                             get_final_pro_answer_prompt)
from app.utils.prompts.query import generate_query_refinement_prompt
from app.utils.prompts.ResponseScoring import scoring_prompt

# Add this near the top of the file
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def user_query_service(query: QueryRequest, is_stream=False):

    message = query.query
    number = query.number
    logger.fatal(f"Initiated conversation for query: {message}")
    context, conversationFound = await get_chat_context(query.conversation_id)
    logger.info(f"Context: {context}")
    conversation_id = query.conversation_id
    messages = await prisma.message.find_many(where={"conversationId": conversation_id})
    logger.fatal(f"Conversation: {messages}")
    if number is None:
        number = 4
    if number > 5:
        number = 4
    updated_query = preprocess_query(message, context)
    prompt = generate_query_refinement_prompt(
        context=context, query=message, refined_query=updated_query)
    # logger.info(f"Prompt: {prompt}")
    return await process_single_query(query, context, is_stream, newQuery=prompt, conversationFound=conversationFound)


async def process_single_query(query: QueryRequest, context: str, is_stream=False, newQuery="", conversationFound=False) -> Dict:

    try:
        message = query.query
        metadata = query.metadata
        refined_query = newQuery
        is_pro = query.is_pro
        start_time = time.time()
        logger.info(
            f"Improving llm query now with {message} and {refined_query}")
        llm_query = improve_query(message, refined_query, context)
        logger.info(f"Improved query: {llm_query}")
        logger.info(
            f"Improve query time: {time.time() - start_time:.4f} seconds")
        logger.info(f"LLM query: {llm_query}")
        pinecone_start = time.time()
        # combined_results = pinecone_query(llm_query, metadata)
        combined_results = await get_final_results_from_memory(
            original_query=message, refined_query=llm_query, metadata=metadata, max_results=10, top_k=15)
        logger.info(
            f"Pinecone query time: {time.time() - pinecone_start:.4f} seconds")

        # print("pinecone result: ", combined_results)
        # print("Combined results: ", combined_results[0])
        chunk_ids = [res['chunkId'] for res in combined_results]
        memIds = [res['memId'] for res in combined_results]

        # Store message in the conversation in the database
        logger.info("Inserting message in the database")
        message = await insert_message_in_db(query_id=query.query_id, chunk_ids=list(set(chunk_ids)), memIds=list(set(memIds)), user_id=query.user_id, conversation_id=query.conversation_id,  user_query=query.query, conversationFound=conversationFound, content=message)
        logger.info("Message inserted in the database")
        mem_data_start = time.time()
        mem_data = await get_all_mems_based_on_chunk_ids(list(set(chunk_ids)))
        logger.info(
            f"Get memory data time: {time.time() - mem_data_start:.4f} seconds")

        complete_data_start = time.time()
        complete_data = ""
        ans_list = []
        logger.info(f'Citations received: {len(chunk_ids)}')
        for i in range(len(chunk_ids)):
            current_ans = {
                "chunk_id": chunk_ids[i],
                "score": [res['score'] for res in combined_results][i],
                "mem_data": [mem.memData for mem in mem_data][i],
                "memId": memIds[i]
            }
            complete_data += f"<data><content>{current_ans['mem_data']}</content>"
            complete_data += f"<data_score>{current_ans['score']}</data_score>"
            # complete_data += f"<cite>{chunk_ids[i]}</cite></data>"
            ans_list.append(current_ans)

        complete_data = f"<question>{llm_query}</question>" + complete_data
        logger.info(
            f"Build complete data time: {time.time() - complete_data_start:.4f} seconds")
        logger.info(f"Message: {message}")
        final_ans_start = time.time()
        final_ans = ""
        # full_text_query1 = prepare_fulltext_query(query.query)
        # full_text_query2 = prepare_fulltext_query(llm_query)

        # full_text_res1 = await prisma_mod.full_text_search(full_text_query1, 10)
        # full_text_res2 = await prisma_mod.full_text_search(full_text_query2, 10)

        # intersection = set(full_text_res1).intersection(set(full_text_res2))

        # print('____-----------_____')

        # print(full_text_res1)
        # print(full_text_res2)

        # print('____-----------_____')
        # logger.info(complete_data)
        if is_pro:
            if is_stream:
                return {
                    "curr_ans": complete_data,
                    "query": llm_query,
                    "prompt": get_final_pro_answer_prompt(query.query, llm_query, context, complete_data, is_stream=True),
                    "messageId": message.id
                }
            final_ans = get_final_pro_answer(
                message, refined_query, context, complete_data)
        else:
            if is_stream:
                return {
                    "curr_ans": complete_data,
                    "query": llm_query,
                    "prompt": final_ans_prompt + complete_data,
                    "messageId": message.id
                }
            final_ans = get_final_answer(complete_data)
        logger.info(
            f"Get final answer time: {time.time() - final_ans_start:.4f} seconds")

        logger.info(
            f"Total process_single_query time: {time.time() - start_time:.4f} seconds")

        result = {
            "query": llm_query,
            "final_ans": convert_newlines(final_ans.content),
            "messageId": message.id,
        }

        return result
    except Exception as e:
        print(f"Error in process_single_query: {str(e)}")
        return {
            "error": str(e)
        }


async def user_multi_query_service2(query: QueryRequest):
    start_time = time.time()

    message = query.query
    metadata = query.metadata
    context,  = get_chat_context(query.conversation_id)

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


async def stream_response(prompt: str, messageId: str) -> AsyncIterator[str]:
    # "got the prompt"
    message_content = ""
    message_id_sent = False
    logger.info(f"Streaming response with prompt: {prompt}")
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


async def get_chat_context(conversation_id: str, limit=2):
    try:
        print("IN 1")
        messages = await prisma.message.find_many(
            where={
                "conversationId": conversation_id
            },
            order={
                "createdAt": "desc"
            })
        queryIds = set()
        for message in messages:
            # print(f"Message sender: {message.sender}, id: {message.id}")
            # print(f"Message content: {message.content}")
            if message.sender != "ai":
                queryIds.add(message.id)
            if len(queryIds) == limit:
                break
        if len(queryIds) == 0:
            return "", len(messages) > 0
        context = {}
        for message in messages:
            if message.id in queryIds:
                print(f"Message id: {message.id}")
                context[message.id] = {
                    "user": message.content
                }
            if message.questionId in queryIds:
                print(f"Question id: {message.questionId}")
                if (message.questionId not in context):
                    context[message.questionId] = {}
                context[message.questionId]["ai"] = message.content

        # print(context)
        final_context = ""
        for key in context.keys():
            final_context += f"User: {context[key]['user']}\nAI: {context[key]['ai']}\n"

        return final_context, len(messages) > 0

    except Exception as e:
        print(f"Error in get_chat_context: {str(e)}")
        return "", len(messages) > 0
