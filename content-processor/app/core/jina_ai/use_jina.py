from app.core.jina_ai import Client

JINA_AI_BASE_URL_SEGMENTATION = 'https://segment.jina.ai/'

jina_seg_client = Client.JinaAIClient(JINA_AI_BASE_URL_SEGMENTATION)

def segment_data(data: str):
    body = {
        'content': data,
        "max_chunk_length": "1000",
        "return_chunks": "true"
    }
    return jina_seg_client.post(data=body)
