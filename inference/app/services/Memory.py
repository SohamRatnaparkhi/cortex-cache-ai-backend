import asyncio
from dataclasses import dataclass
from functools import partial
from logging import getLogger
from typing import Dict, List, Set, Tuple, TypedDict

from app.prisma.prisma import full_text_search, get_all_mems_based_on_chunk_ids
from app.schemas.memory.ApiModel import Results
from app.utils.app_logger_config import logger
from app.utils.Pinecone_query import pinecone_query
from app.utils.Preprocessor import prepare_fulltext_query


class SearchResult(TypedDict):
    """Type definition for search result object."""
    memId: str
    chunkId: str
    score: float
    source: str


@dataclass
class SearchResults:
    """Container for search results from different sources."""
    original_semantic: List[SearchResult]
    refined_semantic: List[SearchResult]
    original_fulltext: List[SearchResult]
    refined_fulltext: List[SearchResult]


class SearchConfig:
    """Configuration parameters for search operations."""
    SEMANTIC_WEIGHT = 0.7
    FULLTEXT_WEIGHT = 0.3
    DEFAULT_TOP_K = 15
    DEFAULT_ABSOLUTE_THRESHOLD = 0.1
    DEFAULT_RELATIVE_THRESHOLD = 0.6
    DEFAULT_RRF_K = 100


async def execute_search_pair(
    search_func,
    original_query: str,
    refined_query: str,
    metadata: dict,
    **kwargs
) -> Tuple[List[SearchResult], List[SearchResult]]:
    """
    Execute a pair of searches (original and refined) concurrently.

    Args:
        search_func: Search function to execute
        original_query: Original search query
        refined_query: Refined version of the query
        metadata: Search metadata
        **kwargs: Additional arguments for search function

    Returns:
        Tuple of results for original and refined queries
    """
    original_search = search_func(original_query, metadata, **kwargs)
    refined_search = search_func(refined_query, metadata, **kwargs)

    return await asyncio.gather(original_search, refined_search)


async def full_text_search_pair(
    original_query: str,
    refined_query: str,
    metadata: dict,
    top_k: int = SearchConfig.DEFAULT_TOP_K
) -> Tuple[List[SearchResult], List[SearchResult]]:
    """
    Perform concurrent full-text searches for both queries.
    """
    prepared_original = prepare_fulltext_query(original_query)
    prepared_refined = prepare_fulltext_query(refined_query)

    return await execute_search_pair(
        full_text_search,
        prepared_original,
        prepared_refined,
        metadata,
        top_k=top_k
    )


async def semantic_search_pair(
    original_query: str,
    refined_query: str,
    metadata: dict,
    top_k: int = SearchConfig.DEFAULT_TOP_K,
    threshold: float = SearchConfig.DEFAULT_ABSOLUTE_THRESHOLD
) -> Tuple[List[SearchResult], List[SearchResult]]:
    """
    Perform concurrent semantic searches for both queries.
    """
    original_results, refined_results = await execute_search_pair(
        pinecone_query,
        original_query,
        refined_query,
        metadata,
        top_k=top_k
    )

    logger.info("Semantic search results - Original: %d, Refined: %d",
                len(original_results), len(refined_results))

    # Filter results by threshold
    filter_by_threshold = partial(
        lambda results, threshold: [
            r for r in results if r["score"] >= threshold]
    )

    return (
        filter_by_threshold(original_results, threshold),
        filter_by_threshold(refined_results, threshold)
    )


def process_search_results(
    semantic_results: Tuple[List[SearchResult], List[SearchResult]],
    fulltext_results: Tuple[List[SearchResult], List[SearchResult]]
) -> SearchResults:
    """
    Process and combine search results with source information.
    """
    original_semantic, refined_semantic = semantic_results
    original_fulltext, refined_fulltext = fulltext_results

    return SearchResults(
        original_semantic=[{**r, "source": "semantic"}
                           for r in original_semantic],
        refined_semantic=[{**r, "source": "semantic"}
                          for r in refined_semantic],
        original_fulltext=[{**r, "source": "full_text"}
                           for r in original_fulltext],
        refined_fulltext=[{**r, "source": "full_text"}
                          for r in refined_fulltext]
    )


def get_unique_chunk_ids(search_results: SearchResults) -> Set[str]:
    """
    Extract unique chunk IDs from SearchResults object.
    """
    all_results = (
        search_results.original_semantic +
        search_results.refined_semantic +
        search_results.original_fulltext +
        search_results.refined_fulltext
    )
    return {result["chunkId"] for result in all_results}


async def get_final_results_from_memory(
    original_query: str,
    refined_query: str,
    metadata: dict,
    top_k: int = SearchConfig.DEFAULT_TOP_K,
    relative_threshold: float = SearchConfig.DEFAULT_RELATIVE_THRESHOLD
) -> List[Results]:
    """
    Perform optimized concurrent search across semantic and full-text methods.
    """
    # Execute both search types concurrently
    semantic_task = semantic_search_pair(
        original_query, refined_query, metadata, top_k)
    fulltext_task = full_text_search_pair(
        original_query, refined_query, metadata, top_k)

    semantic_results, fulltext_results = await asyncio.gather(
        semantic_task, fulltext_task)

    # Process results
    search_results = process_search_results(semantic_results, fulltext_results)

    # Get unique chunk IDs and retrieve memory data
    chunk_ids = get_unique_chunk_ids(search_results)
    memories_data = await get_all_mems_based_on_chunk_ids(chunk_ids)

    # Convert to final results
    return [
        Results(
            memId=memory.memId,
            chunkId=memory.chunkId,
            mem_data=memory.memData
        )
        for memory in memories_data
    ]
