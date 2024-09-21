import asyncio
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncIterator, Dict

from dotenv import load_dotenv
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.schema import HumanMessage
from langchain_groq import ChatGroq

from app.prisma.prisma import get_all_mems_based_on_chunk_ids, prisma
from app.schemas.query.ApiModel import QueryRequest
from app.services.messages import insert_message_in_db
from app.utils.Pinecone_query import pinecone_query
from app.utils.Preprocessor import improve_query, preprocess_query
from app.utils.prompts.final_ans import prompt as final_ans_prompt
from app.utils.prompts.Pro_final_ans import (get_final_pro_answer,
                                             get_final_pro_answer_prompt)
from app.utils.prompts.query import generate_generalized_prompts
from app.utils.prompts.ResponseScoring import scoring_prompt

# Add this near the top of the file
logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)

async def user_query_service(query: QueryRequest, is_stream=False):

    message = query.query
    number = query.number
    context = ""  
    conversation_id = query.conversation_id
    messages = await prisma.message.find_many(where={"conversationId": conversation_id})
    logger.info(f"Conversation: {messages}")
    conversationFound = True
    if messages is not None and len(messages) > 0:
        context = "\n".join(["User: " + m.content if m.sender != 'ai' else "Assistant: " + m.content for m in messages])

    else:
        conversationFound = False
    print("some new context: ", context)
    if number is None:
        number = 4
    if number > 5:
        number = 4
    updated_query = preprocess_query(message, context)
    prompt = generate_generalized_prompts(context=context, query=message, refined_query=updated_query)[number]

    return await process_single_query(query, context, is_stream, newQuery=prompt, conversationFound=conversationFound)

async def process_single_query(query: QueryRequest, context: str, is_stream=False, newQuery = "", conversationFound = False) -> Dict:

    message = query.query
    metadata = query.metadata
    refined_query = newQuery
    is_pro = query.is_pro
    start_time = time.time()
    logger.info(f"Improving llm query now with {message} and {refined_query}")
    llm_query = improve_query(message, refined_query, context)
    logger.info(f"Improve query time: {time.time() - start_time:.4f} seconds")

    pinecone_start = time.time()
    pinecone_result = pinecone_query(llm_query, metadata)
    logger.info(f"Pinecone query time: {time.time() - pinecone_start:.4f} seconds")

    chunk_ids = [res['id'] for res in pinecone_result]
    mem_ids = [res['mem_id'] for res in pinecone_result]

    # Store message in the conversation in the database
    logger.info("Inserting message in the database")
    message = await insert_message_in_db(query_id=query.query_id, chunk_ids=list(set(chunk_ids)), mem_ids=list(set(mem_ids)), user_id=query.user_id, conversation_id=query.conversation_id,  user_query=query.query, conversationFound=conversationFound)
    logger.info("Message inserted in the database")

    mem_data_start = time.time()
    mem_data = await get_all_mems_based_on_chunk_ids(list(set(chunk_ids)))
    logger.info(f"Get memory data time: {time.time() - mem_data_start:.4f} seconds")

    complete_data_start = time.time()
    complete_data = ""
    ans_list = []
    for i in range(len(chunk_ids)):
        current_ans = {
            "chunk_id": chunk_ids[i],
            "score": [res['score'] for res in pinecone_result][i],
            "mem_data": [mem.memData for mem in mem_data][i],
            "mem_id": mem_ids[i]
        }
        complete_data += f"<data>{current_ans['mem_data']}"
        complete_data += f"<data_score>{current_ans['score']}</data_score></data>"
        chunkId = chunk_ids[i].split("_")[-1]
        # complete_data += f"<chunk_id>{chunkId}</chunk_id>"
        # complete_data += f"<mem_id>{mem_ids[i]}</mem_id>"
        ans_list.append(current_ans)
    
    complete_data = f"<question>{llm_query}</question>" + complete_data
    logger.info(f"Build complete data time: {time.time() - complete_data_start:.4f} seconds")
    logger.info(f"Message: {message}")
    final_ans_start = time.time()
    final_ans = ""
    if is_pro:
        if is_stream:
            return {
                "curr_ans": complete_data,
                "query": llm_query,
                "prompt": get_final_pro_answer_prompt(message, refined_query, context, complete_data, is_stream=True),
                "messageId": message.id
            }
        final_ans = get_final_pro_answer(message, refined_query, context, complete_data)
    else:
        if is_stream:
            return {
                "curr_ans": complete_data,
                "query": llm_query,
                "prompt": final_ans_prompt + complete_data,
                "messageId": message.id
            }
        final_ans = get_final_answer(complete_data)
    logger.info(f"Get final answer time: {time.time() - final_ans_start:.4f} seconds")

    logger.info(f"Total process_single_query time: {time.time() - start_time:.4f} seconds")


    result = {
        "query": llm_query,
        "final_ans": convert_newlines(final_ans.content),
        "messageId": message.id,
    }
    
    return result


async def user_multi_query_service2(query: QueryRequest):
    start_time = time.time()

    message = query.query
    metadata = query.metadata
    context = ""  # Assume this is set properly

    updated_query = preprocess_query(message, context)
    refined_queries = generate_generalized_prompts(context=context, query=message, refined_query=updated_query)
    # parallel execution of queries
    results = await asyncio.gather(*[process_single_query(query, context, False, refined_queries) for refined_query in refined_queries])
    all_res_time = time.time() - start_time
    logger.info(f"All results time: {all_res_time:.4f} seconds")

    score_start = time.time()
    scored_answers = score_answers(message, updated_query, context, results[0]["final_ans"], results[1]["final_ans"], results[2]["final_ans"], results[3]["final_ans"], results[4]["final_ans"])
    logger.info(f"Score answers time: {time.time() - score_start:.4f} seconds")
    logger.info(f"Total user_multi_query_service2 time: {time.time() - start_time:.4f} seconds")
    return {
        "scored_answers": scored_answers,
        "final_ans": results
    }

def get_final_answer(curr_ans):
    load_dotenv()

    GROQ_API_KEY = os.getenv("GROQ_API_KEY") 

    os.environ["GROQ_API_KEY"] = GROQ_API_KEY

    llm = ChatGroq(
        model="llama-3.1-70b-versatile",
        temperature=1,
        max_tokens=None,
    timeout=None,
        max_retries=2,
    )
    prompt = final_ans_prompt
    final_ans = llm.invoke(prompt + curr_ans)
    return final_ans

def score_answers(original_query, refined_query, context, answer1, answer2, answer3, answer4, answer5):
    load_dotenv()

    GROQ_API_KEY = os.getenv("GROQ_API_KEY") 

    os.environ["GROQ_API_KEY"] = GROQ_API_KEY

    llm = ChatGroq(
        model="llama-3.1-70b-versatile",
        temperature=1,
        max_tokens=None,
    timeout=None,
        max_retries=2,
    )
    prompt = scoring_prompt(original_query, refined_query, context, answer1, answer2, answer3, answer4, answer5)
    scored_answers = llm.invoke(prompt)
    return scored_answers

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

async def stream_response(prompt: str, messageId: str) -> AsyncIterator[str]:
    # "got the prompt"
    load_dotenv()
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    os.environ["GROQ_API_KEY"] = GROQ_API_KEY
    chat = ChatGroq(
        model="llama-3.1-70b-versatile",
        temperature=1,
        max_tokens=None,
        streaming=True,
        callbacks=[],
        timeout=None,
        max_retries=2
    )
    message_content = ""
    message_id_sent = False
    logger.info(f"Streaming response with prompt: {prompt}")
    try:
        async for chunk in chat.astream([HumanMessage(content=prompt)]):
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

        # Store message in the conversation in the database
        message = await insert_message_in_db(query_id="", chunk_ids=[], mem_ids=[], user_id="", user_query="", content=message_content, only_message=True, message_id=messageId, conversation_id="")
        if message is not None:
            print("Message inserted in db")
    except Exception as e:
        print(f"Error during streaming: {str(e)}")
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
    # Replace double \n with double newline (paragraph break)
    converted = re.sub(r'\n\n', '\n\n', converted)
    return converted