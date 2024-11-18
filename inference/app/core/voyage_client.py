import os
import time
from collections import namedtuple
from typing import List, Tuple

import voyageai
from dotenv import load_dotenv

from app.schemas.memory.ApiModel import Results, ResultsAfterReRanking
from app.schemas.web_agent import ReRankedWebSearchResult, SearchResult
from app.utils.app_logger_config import logger

if os.path.exists(".env"):
    load_dotenv()


vo = voyageai.AsyncClient()

EMBEDDING_BATCH_SIZE = 128

RerankingResult = namedtuple(
    "RerankingResult", ["index", "document", "relevance_score"]
)


class ReRankingConfig:
    MODEL = "rerank-2"
    QUERY_TOKEN_LIMIT = 3500
    BATCH_LIMIT = 1000
    QUERY_DOCUMENT_TOKEN_LIMIT = 16000


async def get_embeddings(documents: list[str]):
    try:
        embeddings = []
        for i in range(0, len(documents), EMBEDDING_BATCH_SIZE):
            batch = documents[i:i + EMBEDDING_BATCH_SIZE]
            emb = await vo.embed(batch, model="voyage-3")
            embeddings.extend(emb.embeddings)

            if (len(documents) / EMBEDDING_BATCH_SIZE) > 4:
                time.sleep(1)
        return embeddings
    except Exception as e:
        logger.error(f"Error getting embeddings: {e}")
        return []


async def re_rank_data(data: List[Results], k: int, query: str, threshold=0.4):
    try:
        re_ranking_results: List[RerankingResult] = []
        documents = [d.mem_data for d in data]

        try:
            for i in range(0, len(documents), ReRankingConfig.BATCH_LIMIT):
                batch = documents[i:i + ReRankingConfig.BATCH_LIMIT]
                res = await vo.rerank(
                    model=ReRankingConfig.MODEL,
                    documents=batch,
                    query=query,
                    top_k=k,
                )
                re_ranking_results.extend(res.results)
        except Exception as e:
            logger.error(f"Error re-ranking data: {e}")
            return None

        final_data: List[ResultsAfterReRanking] = []
        try:
            # Link document data with their memId and chunkId

            for result in re_ranking_results:
                if result.relevance_score < threshold:
                    continue
                final_data.append(
                    ResultsAfterReRanking(
                        memId=data[result.index].memId,
                        chunkId=data[result.index].chunkId,
                        mem_data=data[result.index].mem_data,
                        score=result.relevance_score,
                    )
                )
        except Exception as e:
            logger.error(f"Error linking document data: {e}")
            return final_data

        return final_data
    except Exception as e:
        logger.error(f"Error re-ranking data: {e}")
        return None


async def re_rank_web_data(data: List[SearchResult], k: int, query: str, threshold=0.3):
    try:
        re_ranking_results: List[RerankingResult] = []
        documents = [d.content for d in data]

        try:
            for i in range(0, len(documents), ReRankingConfig.BATCH_LIMIT):
                batch = documents[i:i + ReRankingConfig.BATCH_LIMIT]
                res = await vo.rerank(
                    model=ReRankingConfig.MODEL,
                    documents=batch,
                    query=query,
                    top_k=k,
                )
                re_ranking_results.extend(res.results)
        except Exception as e:
            logger.error(f"Error re-ranking data: {e}")
            return None

        final_data: List[ReRankedWebSearchResult] = []
        try:

            for result in re_ranking_results:
                if result.relevance_score < threshold:
                    continue
                final_data.append(
                    ReRankedWebSearchResult(
                        title=data[result.index].title,
                        url=data[result.index].url,
                        content=data[result.index].content,
                        additional_info=data[result.index].additional_info,
                        score=result.relevance_score,
                    )
                )
        except Exception as e:
            logger.error(f"Error linking document data: {e}")
            return final_data

        return final_data
    except Exception as e:
        logger.error(f"Error re-ranking data: {e}")
        return None


async def unified_rerank(
    memory_data: List[Results] = None,
    web_data: List[SearchResult] = None,
    k: int = 10,
    query: str = "",
    memory_threshold: float = 0.4,
    web_threshold: float = 0.3,
) -> Tuple[List[ResultsAfterReRanking], List[ReRankedWebSearchResult]]:
    """
    Unified function to rerank both memory and web data simultaneously.

    Args:
        memory_data: List of Results objects (can be empty or None)
        web_data: List of SearchResult objects (can be empty or None)
        k: Number of top results to return for each type
        query: Query string for reranking
        memory_threshold: Threshold score for memory results
        web_threshold: Threshold score for web results

    Returns:
        Tuple containing two lists: (reranked_memory_data, reranked_web_data)
        Either list may be empty if input was empty/None
    """
    try:
        # Initialize empty results
        memory_results: List[ResultsAfterReRanking] = []
        web_results: List[ReRankedWebSearchResult] = []

        # Prepare combined documents for reranking
        documents = []
        type_markers = []  # To track the source and index of each document

        # Add memory data if present
        if memory_data:
            for idx, item in enumerate(memory_data):
                documents.append(item.mem_data)
                type_markers.append(('memory', idx))

        # Add web data if present
        if web_data:
            for idx, item in enumerate(web_data):
                if item.get('content'):  # Check if content exists
                    documents.append(item['content'])
                    type_markers.append(('web', idx))

        if not documents:  # If no documents to process
            return [], []

        # Process documents in batches
        all_reranking_results: List[RerankingResult] = []
        try:
            for i in range(0, len(documents), ReRankingConfig.BATCH_LIMIT):
                batch = documents[i:i + ReRankingConfig.BATCH_LIMIT]
                res = await vo.rerank(
                    model=ReRankingConfig.MODEL,
                    documents=batch,
                    query=query,
                    top_k=k,
                )
                all_reranking_results.extend(res.results)
        except Exception as e:
            logger.error(f"Error in batch reranking: {e}")
            return [], []

        # Process results and separate by type
        try:
            for result in all_reranking_results:
                doc_type, original_idx = type_markers[result.index]

                if doc_type == 'memory' and result.relevance_score >= memory_threshold:
                    memory_results.append(
                        ResultsAfterReRanking(
                            memId=memory_data[original_idx].memId,
                            chunkId=memory_data[original_idx].chunkId,
                            mem_data=memory_data[original_idx].mem_data,
                            score=result.relevance_score,
                        )
                    )
                elif doc_type == 'web' and result.relevance_score >= web_threshold:
                    web_results.append(
                        ReRankedWebSearchResult(
                            title=web_data[original_idx]['title'],
                            url=web_data[original_idx]['url'],
                            content=web_data[original_idx]['content'],
                            additional_info=web_data[original_idx]['additional_info'],
                            score=result.relevance_score,
                        )
                    )
        except Exception as e:
            logger.error(f"Error processing reranking results: {e}")
            return memory_results, web_results

        return memory_results, web_results

    except Exception as e:
        logger.error(f"Error in unified reranking: {e}")
        return [], []
