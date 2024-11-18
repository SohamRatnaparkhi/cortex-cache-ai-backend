import os
import time
from collections import namedtuple
from typing import List

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
