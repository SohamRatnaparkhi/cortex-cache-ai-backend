from app.schemas.Metadata import Metadata


def get_vectors(metadata, embeddings):
    vectors = []
    for m, e in zip(metadata, embeddings):
        vector_id = f"{m.mem_id}_{m.specific_desc.chunk_id}"
        vectors.append({
            "id": vector_id,
            "values": e,
            "metadata": flatten_metadata(m),
        })
    return vectors

def flatten_metadata(metadata: Metadata):
    flattened = {}
    
    # Flatten the main Metadata fields
    for key, value in metadata.model_dump().items():
        if key != 'specific_desc':
            if isinstance(value, list):
                flattened[key] = ','.join(map(str, value))
            else:
                flattened[key] = str(value)
    
    # Flatten the specific_desc
    if metadata.specific_desc:
        for key, value in metadata.specific_desc.dict().items():
            flattened[f"specific_desc_{key}"] = str(value)
    
    return flattened