from typing import Union

from app.core import JinaClient

JINA_AI_BASE_URL_SEGMENTATION = 'https://segment.jina.ai/'
JINA_AI_BASE_URL_EMBEDDING = 'https://api.jina.ai/v1/embeddings'

jina_seg_client = JinaClient.JinaAIClient(JINA_AI_BASE_URL_SEGMENTATION)
jina_embed_client = JinaClient.JinaAIClient(JINA_AI_BASE_URL_EMBEDDING)


def segment_data(data: str):
    body = {
        'content': data,
        "max_chunk_length": "1000",
        "return_chunks": "true"
    }
    return jina_seg_client.post(data=body)


def get_embedding(data: list[str], retries=5, task: Union[f'retrieval.query', f'retrieval.passage', f'text-matching'] = 'text-matching'):

    body = {
        'model': 'jina-embeddings-v3',
        'task': task,
        'dimensions': 1024,
        'late_chunking': False,
        'embedding_type': 'float',
        'input': data,
    }

    # body = {
    #     'input': data,
    #     'model': 'jina-embeddings-v2-base-en',
    #     'embedding_type': 'float'
    # }
    # print('Embeddings')
    # print(body)
    # print(res)
    res = jina_embed_client.post(data=body)
    if not res or not res['data']:
        if retries > 0:
            return get_embedding(data, retries - 1)
        return None
    return res
