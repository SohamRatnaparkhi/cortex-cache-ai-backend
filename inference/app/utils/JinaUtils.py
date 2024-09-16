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

def get_embedding(data: list[str]):
    body = {
        'input': data,
        'model': 'jina-embeddings-v2-base-en',
        'embedding_type': 'float'
    }
    return jina_embed_client.post(data=body)
