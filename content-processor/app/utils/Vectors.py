from typing import List

from app.schemas.Metadata import Metadata


def get_vectors(metadata, embeddings):
    vectors = []
    for m, e in zip(metadata, embeddings):
        vector_id = f"{m.memId}_{m.specific_desc.chunk_id}"
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


def combine_data_chunks(chunks: str, meta_chunks: List[Metadata], memId: str, diff=2):
    JOINER = ' <joiner> '
    CENTRAL_OPENER = ' <central> '
    CENTRAL_CLOSER = ' </central> '

    # prev = -diff
    # next = diff

    combined_chunks = []
    for i in range(len(chunks)):
        prev = i - diff
        next = i + diff + 1
        current_chunk = chunks[i]
        current_chunk = CENTRAL_OPENER + current_chunk + CENTRAL_CLOSER
        while prev > 0 and prev < i:
            current_chunk = chunks[prev] + JOINER + current_chunk
            prev += 1
        while next < len(chunks) and next <= i + 2:
            current_chunk = current_chunk + JOINER + chunks[next]
            next += 1
        combined_chunks.append({
            "memData": current_chunk,
            "chunkId": f"{memId}_{i}",
            "metadata": meta_chunks[i].json(),
        })
    # print('chunking done')
    # print(combined_chunks)
    return combined_chunks
