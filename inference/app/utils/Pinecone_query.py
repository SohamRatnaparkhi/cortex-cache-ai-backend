from typing import Any, Dict, List, Union

from app.core import voyage_client
from app.core.PineconeClient import PineconeClient
from app.utils.app_logger_config import logger
from app.utils.JinaUtils import get_embedding


async def pinecone_query(query: str, metadata: dict, top_k: int = 15) -> List[Dict[str, Any]]:
    try:
        pinecone_client = PineconeClient()
        simple_metadata = {}
        range_filters = {}
        text_filters = {}

        for key, value in metadata.items():
            if key in ['tags', 'memory']:
                text_filters[key] = value if isinstance(
                    value, list) else [value]
            else:
                if isinstance(value, (int, float)):
                    range_filters[key] = {'min': value, 'max': value}
                elif isinstance(value, str):
                    text_filters[key] = [value]
                elif isinstance(value, list):
                    text_filters[key] = value
                elif isinstance(value, bool):
                    simple_metadata[key] = value
                else:
                    raise ValueError(
                        f"Unsupported metadata value type: {type(value)}")

        pinecone_filters = get_pinecone_filters(
            simple_metadata, range_filters, text_filters)
        final_query = query if type(query) == str else query[0]
        final_query = final_query if final_query[0] not in [
            "[", "{"] else final_query[1:-1]

        final_query = final_query if final_query[-1] not in [
            "]", "}"] else final_query[:-1]
        # print(f"Final query: {final_query}")

        # vectors_obj = get_embedding([final_query])

        # if not vectors_obj or not vectors_obj['data']:
        #     print("No vectors returned")
        #     return []
        # vectors = vectors_obj['data'][0]['embedding']
        embeddings = await voyage_client.get_embeddings([final_query])
        vectors = embeddings[0]
        res = pinecone_client.query(
            vector=vectors, top_k=top_k, filters=pinecone_filters)
        filtered_res = []
        FILTER_LIMIT = 0.0
        for result in res["matches"]:
            if (result.score < FILTER_LIMIT):
                continue
            filtered_res.append({
                # "metadata": result.metadata,
                "score": result.score,
                "chunkId": result.metadata['specific_desc_chunk_id'],
                "memId": result.metadata['memId']
            })
        logger.info(
            f"pinecone returned {len(filtered_res)} results on query: {query}")
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
            elif len(values) > 1:
                filter_dict[key] = {"$or": [{"$eq": value}
                                            for value in values]}

    return filter_dict


def get_pinecone_filters(metadata: Dict[str, Any],
                         range_filters: Dict[str, Dict[str,
                                                       Union[int, float]]] = None,
                         text_filters: Dict[str, List[str]] = None) -> Dict[str, Any]:
    base_filter = create_pinecone_filter(metadata)
    final_filter = apply_advanced_filters(
        base_filter, range_filters, text_filters)

    logger.info(f"Generated Pinecone filters: {final_filter}")
    return final_filter


def generate_pinecone_query(metadata: Dict[str, Any]) -> Dict[str, Any]:
    simple_metadata = {}
    range_filters = {}
    text_filters = {}

    for key, value in metadata.items():
        if key in ['tags', 'memory']:
            text_filters[key] = value if isinstance(value, list) else [value]
        else:
            if isinstance(value, (int, float)):
                range_filters[key] = {'min': value, 'max': value}
            elif isinstance(value, str):
                text_filters[key] = [value]
            elif isinstance(value, list):
                text_filters[key] = value
            elif isinstance(value, bool):
                simple_metadata[key] = value
            else:
                raise ValueError(
                    f"Unsupported metadata value type: {type(value)}")

    pinecone_filters = get_pinecone_filters(
        simple_metadata, range_filters, text_filters)
    print(f"Generated Pinecone query: {pinecone_filters}")
    return pinecone_filters
    # return {"$and": [final_filter]} if len(final_filter) > 1 else final_filter
