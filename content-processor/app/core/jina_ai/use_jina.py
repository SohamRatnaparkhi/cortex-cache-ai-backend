import asyncio
from typing import Any, Dict, List, Optional, Union

from app.core.jina_ai import Client

JINA_AI_BASE_URL_SEGMENTATION = 'https://segment.jina.ai/'
JINA_AI_BASE_URL_EMBEDDING = 'https://api.jina.ai/v1/embeddings'
JINA_AI_BASE_WEB_SCRAPER = 'https://r.jina.ai/'

jina_seg_client = Client.JinaAIClient(JINA_AI_BASE_URL_SEGMENTATION)
jina_embed_client = Client.JinaAIClient(JINA_AI_BASE_URL_EMBEDDING)


def segment_data(data: str):

    data = data.replace('\n', ' ')

    body = {
        'content': data,
        "tokenizer": "o200k_base",
        "max_chunk_length": "800",
        "return_chunks": "true"
    }

    MAX_CHAR_LENGTH = 30000
    final_res = []

    for i in range(0, len(data), MAX_CHAR_LENGTH):
        current_data = data[i:i + MAX_CHAR_LENGTH]
        body['content'] = current_data

        # Attempt to post data and handle potential errors
        try:
            res = jina_seg_client.post(data=body)
            if res is not None and "chunks" in res.keys():
                final_res.extend(res["chunks"])
            else:
                print(f'Error in response for input chunk: {current_data}')
        except Exception as e:
            print(
                f'Exception occurred while processing input chunk: {current_data}. Error: {e}')
            return []
    return final_res


def get_embedding(data: List[str], task: Union[str, None] = 'retrieval.passage', retry: int = 5) -> List:
    body = {
        'model': 'jina-embeddings-v3',
        'task': task,
        'dimensions': 1024,
        'late_chunking': False,
        'embedding_type': 'float',
    }

    SINGLE_REQUEST_LIMIT = 30
    final_res = []

    for i in range(0, len(data), SINGLE_REQUEST_LIMIT):
        # print(data)
        current_data = data[i:i + SINGLE_REQUEST_LIMIT]
        body['input'] = current_data

        # Attempt to post data and handle potential errors
        try:
            res = jina_embed_client.post(data=body)
            print("Got once")
            if res is not None and "data" in res.keys():
                print(res.keys())
                final_res.extend(res["data"])
            else:
                print(f'Error in response for input chunk: {current_data}')
        except Exception as e:
            print(
                f'Exception occurred while processing input chunk: {current_data}. Error: {e}')
            if retry > 0:
                return get_embedding(data, task, retry - 1)

    return final_res


async def web_scraper(link: str, max_retries: int = 10, retry_delay: float = 1.0) -> Optional[Dict[Any, Any]]:
    print("URL: ", JINA_AI_BASE_WEB_SCRAPER + link)

    jina_web_scraper_client = Client.JinaAIClient(
        JINA_AI_BASE_WEB_SCRAPER + link, isReader=True)
    for retry in range(max_retries):
        try:
            response = await jina_web_scraper_client.get()
            if response is not None and response.get("data") is not None:
                # print(f"Web Scraper Response: {response}")
                return response

            # If we didn't get valid data, wait before retrying
            # This allows other tasks to run during the wait
            jina_web_scraper_client.retry += 1
            print(
                f"Attempt {retry + 1} failed, retrying after {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)

        except Exception as e:
            print(f"Error during attempt {retry + 1}: {str(e)}")
            await asyncio.sleep(retry_delay)

    print(f"Failed to get valid response after {max_retries} attempts")
    return None
