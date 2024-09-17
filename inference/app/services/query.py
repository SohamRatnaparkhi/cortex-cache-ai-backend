import asyncio
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from app.prisma.prisma import get_all_mems_based_on_chunk_ids
from app.schemas.query.ApiModel import QueryRequest
from app.utils.Pinecone_query import pinecone_query
from app.utils.Preprocessor import improve_query, preprocess_query
from app.utils.prompts.final_ans import prompt as final_ans_prompt
from app.utils.prompts.query import generate_generalized_prompts
from app.utils.prompts.ResponseScoring import scoring_prompt

# Add this near the top of the file
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def user_query_service(query: QueryRequest):

    message = query.query
    metadata = query.metadata
    number = query.number
    context = ""
    if number is None:
        number = 4
    if number > 5:
        number = 4
    updated_query = preprocess_query(message, context)
    prompt = generate_generalized_prompts(context=context, query=message, refined_query=updated_query)[number]

    return await process_single_query(message, context, prompt, metadata)

async def process_single_query(message, context, refined_query: str, metadata: Dict) -> Dict:
    start_time = time.time()

    llm_query = improve_query(message, refined_query, context)
    query_temp = f"<question>{llm_query}</question>" 
    logger.info(f"Improve query time: {time.time() - start_time:.4f} seconds")

    pinecone_start = time.time()
    pinecone_result = pinecone_query(llm_query, metadata)
    logger.info(f"Pinecone query time: {time.time() - pinecone_start:.4f} seconds")

    chunk_ids = [res['id'] for res in pinecone_result]
    mem_ids = [res['mem_id'] for res in pinecone_result]

    mem_data_start = time.time()
    mem_data = await get_all_mems_based_on_chunk_ids(list(set(chunk_ids)))
    logger.info(f"Get mem data time: {time.time() - mem_data_start:.4f} seconds")

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
        complete_data += f"<chunk_id>{chunkId}</chunk_id>"
        complete_data += f"<mem_id>{mem_ids[i]}</mem_id>"
        ans_list.append(current_ans)
    
    complete_data = f"<question>{llm_query}</question>" + complete_data
    logger.info(f"Build complete data time: {time.time() - complete_data_start:.4f} seconds")

    final_ans_start = time.time()
    final_ans = get_final_answer(complete_data)
    logger.info(f"Get final answer time: {time.time() - final_ans_start:.4f} seconds")

    logger.info(f"Total process_single_query time: {time.time() - start_time:.4f} seconds")

    result = {
        "query": llm_query,
        "final_ans": final_ans.content,
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
    results = await asyncio.gather(*[process_single_query(message, context,refined_query, metadata) for refined_query in refined_queries])
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