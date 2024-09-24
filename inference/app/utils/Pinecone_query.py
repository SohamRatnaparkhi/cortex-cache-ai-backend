from typing import Any, Dict, List, Union

from app.core.PineconeClient import PineconeClient
from app.utils.JinaUtils import get_embedding


def pinecone_query(query: str, metadata: dict):
    try:
        pinecone_client = PineconeClient()
        simple_metadata = {}
        range_filters = {}
        text_filters = {}
        for key, value in metadata.items():
            if key == 'tags':
                text_filters[key] = value
            else:
                if isinstance(value, (int, float)):
                    range_filters[key] = value
                elif isinstance(value, str):
                    text_filters[key] = [value]
                else:
                    raise ValueError(
                        f"Unsupported metadata value type: {type(value)}")
        pinecone_filters = get_pinecone_filters(
            simple_metadata, range_filters, text_filters)
        vectors_obj = get_embedding([query])

        if not vectors_obj or not vectors_obj['data']:
            print("No vectors returned")
            return []
        vectors = vectors_obj['data'][0]['embedding']
        res = pinecone_client.query(
            vector=vectors, top_k=15, filters=pinecone_filters)
        print("pinecone returned")
        filtered_res = []
        for result in res["matches"]:
            if (result.score < 0.70):
                continue
            filtered_res.append({
                "metadata": result.metadata,
                "score": result.score,
                "id": result.metadata['specific_desc_chunk_id'],
                "mem_id": result.metadata['mem_id']
            })
        return filtered_res
    except Exception as e:
        print(f"Error in pinecone_query: {str(e)}")
        return {[]}  # Return error message


def create_pinecone_filter(metadata: Dict[str, Any]) -> Dict[str, Any]:
    def process_value(value: Any) -> Dict[str, Any]:
        if isinstance(value, (int, float, str)):
            return {"$eq": value}
        elif isinstance(value, list):
            return {"$in": value}
        elif value is None:
            return {"$exists": False}
        elif isinstance(value, bool):
            return {"$eq": value}
        else:
            raise ValueError(f"Unsupported metadata value type: {type(value)}")

    filter_dict = {}
    for key, value in metadata.items():
        filter_dict[key] = process_value(value)

    return filter_dict


def apply_advanced_filters(base_filter: Dict[str, Any],
                           range_filters: Dict[str, Dict[str,
                                                         Union[int, float]]] = None,
                           text_filters: Dict[str, List[str]] = None) -> Dict[str, Any]:
    filter_dict = base_filter.copy()

    if range_filters:
        for key, range_value in range_filters.items():
            min_val, max_val = range_value.get('min'), range_value.get('max')
            if min_val is not None and max_val is not None:
                filter_dict[key] = {"$gte": min_val, "$lte": max_val}
            elif min_val is not None:
                filter_dict[key] = {"$gte": min_val}
            elif max_val is not None:
                filter_dict[key] = {"$lte": max_val}

    if text_filters:
        for key, values in text_filters.items():
            if len(values) == 1:
                filter_dict[key] = {"$eq": values[0]}
            else:
                filter_dict[key] = {"$in": values}

    return filter_dict


def get_pinecone_filters(metadata: Dict[str, Any],
                         range_filters: Dict[str, Dict[str,
                                                       Union[int, float]]] = None,
                         text_filters: Dict[str, List[str]] = None) -> Dict[str, Any]:
    base_filter = create_pinecone_filter(metadata)
    final_filter = apply_advanced_filters(
        base_filter, range_filters, text_filters)
    return {"$and": [final_filter]} if len(final_filter) > 1 else final_filter
