from typing import List, Union

from app.core.jina_ai import Client

JINA_AI_BASE_URL_SEGMENTATION = 'https://segment.jina.ai/'
JINA_AI_BASE_URL_EMBEDDING = 'https://api.jina.ai/v1/embeddings'
JINA_AI_BASE_WEB_SCRAPER = 'https://r.jina.ai/'

jina_seg_client = Client.JinaAIClient(JINA_AI_BASE_URL_SEGMENTATION)
jina_embed_client = Client.JinaAIClient(JINA_AI_BASE_URL_EMBEDDING)


def segment_data(data: str):
    body = {
        'content': data,
        "tokenizer": "o200k_base",
        "max_chunk_length": "1200",
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


def web_scraper(link: str):
    print("URL: ", JINA_AI_BASE_WEB_SCRAPER + link)
    jina_web_scraper_client = Client.JinaAIClient(
        JINA_AI_BASE_WEB_SCRAPER + link, isReader=True)
    print(jina_web_scraper_client.isReader)
    return jina_web_scraper_client.get()
