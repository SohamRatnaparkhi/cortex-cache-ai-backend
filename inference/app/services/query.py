import asyncio
import os
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


async def user_query_service(query: QueryRequest):

    message = query.query
    metadata = query.metadata

    # TODO: get user id, chat id and mem id (if available) from query metadata
    # TODO: preprocess query
    # TODO: get chat context from chat id
    context = ""
    # TODO: truncate context and combine it with query
    updated_query = preprocess_query(message, context)

    # TODO: send combination to LLM to refine it and get a logical single short query with some points included from context if required and short summarized context
    llm_query = improve_query(message, updated_query, context)
    # TODO: query to pinecone with this query and metadata to get top k results
    pinecone_res = pinecone_query(llm_query, metadata);
    # TODO: combine chunks of context and send to LLM to get final response
    chunk_ids = [res['id'] for res in pinecone_res]
    mems = await get_all_mems_based_on_chunk_ids(chunk_ids)
    mems_data = [mem.memData for mem in mems]
    return {
        "updated_query": updated_query,
        "llm_query": llm_query,
        "pinecone_res": pinecone_res,
        "mems_data": mems_data
    }

async def process_single_query(message, context, refined_query: str, metadata: Dict) -> Dict:
    # Execute Pinecone query
    llm_query = improve_query(message, refined_query, context)
    query_temp = f"<question>{llm_query}</question>" 

    pinecone_result = pinecone_query(llm_query, metadata)

    # Extract chunk IDs
    chunk_ids = [res['id'] for res in pinecone_result]
    mem_ids = [res['mem_id'] for res in pinecone_result]
    # Fetch memory data
    mem_data = await get_all_mems_based_on_chunk_ids(list(set(chunk_ids)))

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
    
    # print(complete_data)
    # Prepare result
    complete_data = f"<question>{llm_query}</question>" + complete_data
    final_ans = get_final_answer(complete_data)
    print("Got final answer for query: ", llm_query)
    result = {
        "query": llm_query,
        "final_ans": final_ans.content,
    }
    
    return result


async def user_multi_query_service2(query: QueryRequest):
    message = query.query
    metadata = query.metadata
    context = ""  # Assume this is set properly

    updated_query = preprocess_query(message, context)
    print("preprocessing done")
    refined_queries = generate_generalized_prompts(context=context, query=message, refined_query=updated_query)
    print("refined queries generated")
    # parallel execution of queries
    results = await asyncio.gather(*[process_single_query(message, context,refined_query, metadata) for refined_query in refined_queries])
    print("got all results")
    print("scoring starts")
    scored_answers = score_answers(message, updated_query, context, results[0]["final_ans"], results[1]["final_ans"], results[2]["final_ans"], results[3]["final_ans"], results[4]["final_ans"])

    print(scored_answers)
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