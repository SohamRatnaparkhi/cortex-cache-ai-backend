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


def combine_data_chunks(chunks: str, meta_chunks: List[Metadata], memId: str, diff=1):
    JOINER = '<joiner>'
    CENTRAL_OPENER = '<central>'
    CENTRAL_CLOSER = '</central>'

    combined_chunks = []
    for i in range(len(chunks)):
        # Calculate bounds
        prev = max(0, i - diff)
        next = min(len(chunks), i + diff + 1)

        # Build the combined chunk
        parts = []

        # Add previous chunks with joiners
        if prev < i:
            parts.extend([f"{chunks[j]} {JOINER}" for j in range(prev, i)])

        # Add central chunk
        parts.append(f"{CENTRAL_OPENER}{chunks[i]}{CENTRAL_CLOSER}")

        # Add next chunks with joiners
        if i + 1 < next:
            parts.extend([f"{JOINER} {chunks[j]}" for j in range(i + 1, next)])

        # Join all parts
        current_chunk = ' '.join(parts)

        combined_chunks.append({
            "memData": current_chunk,
            "chunkId": f"{memId}_{i}",
            "metadata": meta_chunks[i].json(),
        })

    return combined_chunks
