from typing import Union

from app.core.jina_ai import Client

JINA_AI_BASE_URL_SEGMENTATION = 'https://segment.jina.ai/'
JINA_AI_BASE_URL_EMBEDDING = 'https://api.jina.ai/v1/embeddings'

jina_seg_client = Client.JinaAIClient(JINA_AI_BASE_URL_SEGMENTATION)
jina_embed_client = Client.JinaAIClient(JINA_AI_BASE_URL_EMBEDDING)


def segment_data(data: str):
    body = {
        'content': data,
        "max_chunk_length": "1200",
        "return_chunks": "true"
    }
    return jina_seg_client.post(data=body)


def get_embedding(data: list[str], task: Union[f'retrieval.query', f'retrieval.passage'] = 'retrieval.passage'):
    body = {
        'model': 'jina-embeddings-v3',
        'task': task,
        'dimensions': 1024,
        'late_chunking': False,
        'embedding_type': 'float',
        'input': data,
    }
    return jina_embed_client.post(data=body)
