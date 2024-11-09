
from typing import Dict, List, Tuple

from app.services.Memory import SearchConfig, SearchResult
from app.utils.app_logger_config import logger


def re_rank_using_voyager(
    search_results: List[SearchResult],
    top_k: int = SearchConfig.DEFAULT_TOP_K,
    refined_query: str = ""
) -> List[SearchResult]:
    """
    Re-rank search results using the Voyager model.

    Args:
        search_results: List of search results
        top_k: Number of top results to return

    Returns:
        Re-ranked search results
    """


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


def scale_score(score: float) -> float:
    """
    Scale the search score.

    Args:
        score: Original score

    Returns:
        Scaled score
    """
    return score * 100
