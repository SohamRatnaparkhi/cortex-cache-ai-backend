from dataclasses import dataclass
from logging import getLogger
from typing import Dict, List, Set, Tuple, TypedDict

from app.prisma.prisma import full_text_search, get_all_mems_based_on_chunk_ids
from app.schemas.memory.ApiModel import Results
from app.utils.Pinecone_query import pinecone_query
from app.utils.Preprocessor import prepare_fulltext_query

logger = getLogger(__name__)


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


def get_semantic_search_results(
    original_query: str,
    refined_query: str,
    metadata: dict,
    top_k: int = SearchConfig.DEFAULT_TOP_K,
    threshold: float = SearchConfig.DEFAULT_ABSOLUTE_THRESHOLD
) -> Tuple[List[SearchResult], List[SearchResult]]:
    """
    Perform semantic search for both original and refined queries.

    Args:
        original_query: Original search query
        refined_query: Refined version of the search query
        metadata: Search metadata
        top_k: Number of top results to return
        threshold: Minimum score threshold

    Returns:
        Tuple of filtered results for original and refined queries
    """
    refined_results = pinecone_query(refined_query, metadata, top_k)
    original_results = pinecone_query(original_query, metadata, top_k)

    logger.info("Semantic search results - Original: %d, Refined: %d",
                len(original_results), len(refined_results))

    return (
        [res for res in original_results if res["score"] >= threshold],
        [res for res in refined_results if res["score"] >= threshold]
    )


async def get_full_text_search_results(
    original_query: str,
    refined_query: str,
    metadata: dict,
    top_k: int = SearchConfig.DEFAULT_TOP_K
) -> Tuple[List[SearchResult], List[SearchResult]]:
    """
    Perform full-text search for both original and refined queries.

    Args:
        original_query: Original search query
        refined_query: Refined version of the search query
        metadata: Search metadata
        top_k: Number of top results to return

    Returns:
        Tuple of results for original and refined queries
    """
    original_results = await full_text_search(
        prepare_fulltext_query(original_query), metadata, top_k)
    refined_results = await full_text_search(
        prepare_fulltext_query(refined_query), metadata, top_k)

    return original_results, refined_results


def reciprocal_rank_fusion(
    result_lists: List[List[SearchResult]],
    k: int = SearchConfig.DEFAULT_RRF_K
) -> List[Tuple[str, str, float]]:
    """
    Implement reciprocal rank fusion to combine multiple result lists.

    Args:
        result_lists: List of search result lists to combine
        k: RRF constant

    Returns:
        Combined and ranked results
    """
    fused_scores: Dict[Tuple[str, str], float] = {}

    for results in result_lists:
        for rank, result in enumerate(results):
            doc_key = (result["memId"], result["chunkId"])
            weight = (SearchConfig.SEMANTIC_WEIGHT
                      if result["source"] == "semantic"
                      else SearchConfig.FULLTEXT_WEIGHT)

            if not isinstance(result["score"], (int, float)):
                logger.warning("Invalid score type for %s: %s",
                               doc_key, type(result["score"]))
                continue

            score = (weight / (rank + k)) * scale_score(result["score"])
            fused_scores[doc_key] = fused_scores.get(doc_key, 0) + score

    return sorted(
        [(memId, chunkId, score)
         for (memId, chunkId), score in fused_scores.items()],
        key=lambda x: x[2],
        reverse=True
    )


def apply_relative_threshold(
    fused_results: List[Tuple[str, str, float]],
    relative_threshold: float = SearchConfig.DEFAULT_RELATIVE_THRESHOLD
) -> List[SearchResult]:
    """
    Apply relative threshold to fused results.

    Args:
        fused_results: List of fused search results
        relative_threshold: Threshold relative to top score

    Returns:
        Filtered results above threshold
    """
    if not fused_results:
        return []

    top_score = max(fused_results[0][2], relative_threshold / 2)
    threshold = top_score * relative_threshold

    logger.debug("Applying relative threshold: %f", threshold)

    return [
        {"memId": memId, "chunkId": chunkId, "score": score}
        for memId, chunkId, score in fused_results
        if score >= threshold
    ]


def get_unique_chunk_ids(result_lists: List[List[SearchResult]]) -> Set[str]:
    """
    Extract unique chunk IDs from result lists.

    Args:
        result_lists: List of search result lists

    Returns:
        Set of unique chunk IDs
    """
    return {result["chunkId"] for results in result_lists for result in results}


async def get_final_results_from_memory(
    original_query: str,
    refined_query: str,
    metadata: dict,
    top_k: int = SearchConfig.DEFAULT_TOP_K,
    relative_threshold: float = SearchConfig.DEFAULT_RELATIVE_THRESHOLD
) -> List[Results]:
    """
    Perform comprehensive search across semantic and full-text methods.

    Args:
        original_query: Original search query
        refined_query: Refined version of the query
        metadata: Search metadata
        top_k: Number of top results to return
        relative_threshold: Threshold for filtering results

    Returns:
        Combined and processed search results
    """
    # Get results from both search methods
    semantic_results = get_semantic_search_results(
        original_query, refined_query, metadata, top_k)
    fulltext_results = await get_full_text_search_results(
        original_query, refined_query, metadata, top_k)

    # Add source information to results
    search_results = SearchResults(
        original_semantic=[{**r, "source": "semantic"}
                           for r in semantic_results[0]],
        refined_semantic=[{**r, "source": "semantic"}
                          for r in semantic_results[1]],
        original_fulltext=[{**r, "source": "full_text"}
                           for r in fulltext_results[0]],
        refined_fulltext=[{**r, "source": "full_text"}
                          for r in fulltext_results[1]]
    )

    # Combine non-empty result lists
    result_lists = [
        results for results in [
            search_results.original_semantic,
            search_results.refined_semantic,
            search_results.original_fulltext,
            search_results.refined_fulltext
        ]
        if results
    ]

    logger.info("Combined %d result lists", len(result_lists))

    # Get unique chunk IDs and retrieve memory data
    chunk_ids = get_unique_chunk_ids(result_lists)
    memories_data = await get_all_mems_based_on_chunk_ids(chunk_ids)

    # Convert to final results format
    return [
        Results(
            memId=memory.memId,
            chunkId=memory.chunkId,
            mem_data=memory.memData
        )
        for memory in memories_data
    ]


def scale_score(score: float) -> float:
    """
    Scale the search score.

    Args:
        score: Original score

    Returns:
        Scaled score
    """
    return score * 100
