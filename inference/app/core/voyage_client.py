import asyncio
import json
import os
import re
import time
from collections import namedtuple
from itertools import islice
from typing import Dict, List, Optional, Tuple

import voyageai
from dotenv import load_dotenv

from app.schemas.memory.ApiModel import Results, ResultsAfterReRanking
from app.schemas.web_agent import ReRankedWebSearchResult, SearchResult
# from app.services.query import process_gemini_response
from app.utils import llms
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
                            source=web_data[original_idx]['source'],
                            score=result.relevance_score,
                        )
                    )
        except Exception as e:
            logger.error(f"Error processing reranking results: {e}")
            return memory_results, web_results

        # sort results based on score
        memory_results.sort(key=lambda x: x.score, reverse=True)
        web_results.sort(key=lambda x: x.score, reverse=True)

        return memory_results, web_results

    except Exception as e:
        logger.error(f"Error in unified reranking: {e}")
        return [], []

BATCH_SIZE = 10
MAX_CONCURRENT_BATCHES = 3


def create_reranking_prompt(query: str, documents: List[str]) -> str:
    """
    Creates a prompt for reranking documents with enhanced scoring granularity
    """
    formatted_docs = [{"index": i, "text": doc}
                      for i, doc in enumerate(documents)]

    prompt = f"""Analyze and score document relevance to query: "{query}"

# Scoring Protocol
1. Relevance Dimensions:
- Contextual Alignment: Does the document directly address the query's core subject?
- Specificity Match: Contains specific entities/terms from query?
- Scope Coverage: Percentage of query aspects addressed
- Signal Quality: Clear information vs filler content ratio

2. Scoring Matrix:
0.95-1.0 = Exact match (all dimensions satisfied + extra context)
0.85-0.94 = Near-perfect match (minor missing elements)
0.75-0.84 = Strong relevance (core subject addressed)
0.55-0.74 = Partial relevance (some related concepts)
0.45-0.5 = Weak connection (tangential mentions)
0.0-0.44 = Irrelevant (score as 0.0)

3. Penalty Rules:
- -0.3 for containing contradictory information
- -0.2 for off-topic sections >30% of content
- -0.1 for keyword stuffing without context

# Processing Guidelines
1. Compare documents relatively before final scoring
2. Prioritize specificity over general information
3. Treat document length neutrally unless affecting relevance
4. Score decisively - avoid 0.4-0.6 range unless ambiguous

Input Documents:
{json.dumps(formatted_docs, indent=2)}

# Output Requirements - STRICT JSON OUTPUT WITH NO ADDITIONAL TEXT and COMMENTS
Return JSON array with ALL original indexes (JSON array):
[
  {{"index": 0, "score": 0.95}},
  {{"index": 2, "score": 0.75}}
]"""

    return prompt


def process_gemini_response_json(response) -> Tuple[Optional[str], Optional[Dict]]:
    """
    Processes Gemini API response with enhanced JSON parsing resilience
    """
    try:
        # Extract response content
        text = response.candidates[0].content.parts[0].text
        token_counts = {
            'prompt_tokens': response.usage_metadata.prompt_token_count,
            'completion_tokens': response.usage_metadata.candidates_token_count,
            'total_tokens': response.usage_metadata.total_token_count
        }

        # Normalize response text
        text = text.strip()
        clean_text = re.sub(r'^```json|```$', '', text,
                            flags=re.MULTILINE).strip()

        # Attempt direct JSON parsing
        try:
            json.loads(clean_text)
            return clean_text, token_counts
        except json.JSONDecodeError as e:
            logger.debug(
                f"Initial JSON parse failed, attempting recovery: {e}")

        # Fallback 1: Find JSON in malformed responses
        json_pattern = r'\[\s*{.*?}\s*\]'  # Array of objects pattern
        matches = re.findall(json_pattern, clean_text, re.DOTALL)

        if matches:
            # Try longest match first (most likely candidate)
            matches.sort(key=len, reverse=True)
            for match in matches:
                try:
                    # Clean common formatting issues
                    sanitized = re.sub(
                        r'(?<=\{|\,)\s*(\w+)(?=:)', r'"\1"', match)
                    parsed = json.loads(sanitized)
                    if validate_reranking_json(parsed):
                        return json.dumps(parsed), token_counts
                except json.JSONDecodeError:
                    continue

        # Fallback 2: Find any JSON-like structures
        bracket_pattern = r'\{.*?\}'  # Any object pattern
        objects = re.findall(bracket_pattern, clean_text, re.DOTALL)
        valid_objects = []

        for obj in objects:
            try:
                sanitized = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', obj)
                parsed = json.loads(sanitized)
                if {'index', 'score'}.issubset(parsed.keys()):
                    valid_objects.append(parsed)
            except Exception:
                continue

        if valid_objects:
            return json.dumps(valid_objects), token_counts

        logger.error("Failed to parse JSON from response")
        return None, token_counts

    except Exception as e:
        logger.error(f"Error processing response: {str(e)}")
        logger.debug(f"Problematic response content: {text}")
        return None, None


def validate_reranking_json(data) -> bool:
    """Validates reranking JSON structure"""
    if not isinstance(data, list):
        return False
    return all(
        isinstance(item, dict) and
        'index' in item and
        'score' in item
        for item in data
    )


async def process_batch(
    query: str,
    batch_data: List[tuple],
    start_idx: int,
) -> List[dict]:
    """
    Process a single batch of documents through Gemini.
    """
    try:
        # Extract document content
        documents = [item[2] for item in batch_data]

        # Create prompt
        prompt = create_reranking_prompt(query, documents)

        # Get response from Gemini
        model = llms.gemini_model
        response = await model.generate_content_async(prompt)

        # Process response
        text, _ = process_gemini_response_json(response)
        if not text:
            return []

        try:
            # Parse JSON response
            ranking_results = json.loads(text)

            # Validate response format
            if not isinstance(ranking_results, list):
                logger.error("Invalid response format: not a list")
                return []

            # Adjust indices for batch offset
            for item in ranking_results:
                if 'index' in item and 'score' in item:
                    item['index'] = item['index'] + start_idx

            return ranking_results

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return []

    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        return []


async def unified_rerank_gemini(
    memory_data: List[Results] = None,
    web_data: List[SearchResult] = None,
    k: int = 10,
    query: str = "",
    memory_threshold: float = 0.40,
    web_threshold: float = 0.5,
) -> Tuple[List[ResultsAfterReRanking], List[ReRankedWebSearchResult]]:
    """
    Rerank memory and web data using Gemini with parallel batching.
    """
    try:
        if not memory_data and not web_data:
            return [], []

        # Prepare combined data
        all_data = []
        if memory_data:
            all_data.extend([("memory", i, item.mem_data)
                             for i, item in enumerate(memory_data)])
        if web_data:
            all_data.extend([("web", i, item['content'])
                             for i, item in enumerate(web_data)
                             if item.get('content')])

        # Create batches
        BATCH_SIZE = 10
        batches = []
        for i in range(0, len(all_data), BATCH_SIZE):
            batches.append(all_data[i:i + BATCH_SIZE])

        # Process batches with semaphore
        MAX_CONCURRENT_BATCHES = 3
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCHES)

        async def process_batch_with_semaphore(batch, start_idx):
            async with semaphore:
                return await process_batch(query, batch, start_idx)

        # Run batches concurrently
        tasks = [
            process_batch_with_semaphore(batch, i * BATCH_SIZE)
            for i, batch in enumerate(batches)
        ]
        batch_results = await asyncio.gather(*tasks)

        # Combine results
        all_rankings = []
        for batch in batch_results:
            all_rankings.extend(batch)

        if len(all_rankings) == 0:
            return unified_rerank(memory_data, web_data, k, query, memory_threshold, web_threshold)

        # Process rankings
        memory_results = []
        web_results = []

        for ranking in all_rankings:
            try:
                idx = ranking['index']
                score = float(ranking['score'])
                data_type, original_index, _ = all_data[idx]

                if data_type == "memory" and score >= memory_threshold:
                    memory_results.append(
                        ResultsAfterReRanking(
                            memId=memory_data[original_index].memId,
                            chunkId=memory_data[original_index].chunkId,
                            mem_data=filter_content_in_memory_data(
                                memory_data[original_index].mem_data),
                            score=score,
                        )
                    )
                elif data_type == "web" and score >= web_threshold:
                    web_results.append(
                        ReRankedWebSearchResult(
                            title=web_data[original_index]['title'],
                            url=web_data[original_index]['url'],
                            content=web_data[original_index].get(
                                'content', ""),
                            additional_info=web_data[original_index]['additional_info'],
                            source=web_data[original_index]['source'],
                            score=score,
                        )
                    )
            except (KeyError, IndexError) as e:
                logger.error(f"Error processing ranking result: {e}")
                continue

        memory_results.sort(key=lambda x: x.score, reverse=True)
        web_results.sort(key=lambda x: x.score, reverse=True)

        return memory_results[:k], web_results[:k]

    except Exception as e:
        logger.error(f"Error in unified reranking: {e}")
        return unified_rerank(memory_data, web_data, k, query, memory_threshold, web_threshold)


def filter_content_in_memory_data(data: str) -> str:
    if not data:
        return ""

    # Extract central content
    central_match = re.search(r'<central>(.*?)</central>', data, re.DOTALL)
    central_content = central_match.group(1) if central_match else ""

    # Extract joiner content
    joiner_matches = re.finditer(r'<joiner>(.*?)</joiner>', data, re.DOTALL)
    joiner_content = []

    for match in joiner_matches:
        text = match.group(1)
        # Split on periods and take max 2 sentences
        sentences = [s.strip() + '.' for s in text.split('.') if s.strip()]
        joiner_content.append("".join(sentences[:2]))

    # Combine all content
    filtered_content = f"{central_content} {' '.join(joiner_content)}"

    # Remove any remaining tags
    filtered_content = re.sub(r'<[^>]+>', '', filtered_content)

    # Clean up whitespace
    ans = ' '.join(filtered_content.split())

    if len(ans) < 20:
        return data
    return ans
