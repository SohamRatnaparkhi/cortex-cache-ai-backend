import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import List

from app.core.web_agent import WebAgent
from app.schemas.web_agent import SearchResult
from app.services.search import search_searxng

agent = WebAgent(search_searxng)


async def get_web_results(query: str, web_sources: List[str], web_agent: WebAgent = agent) -> List[SearchResult]:
    """
    Fetch search results from multiple web sources concurrently.

    Args:
        query: Search query string
        web_sources: List of web source types (e.g., ["web", "youtube", "reddit"])
        web_agent: Instance of WebAgent class

    Returns:
        List of SearchResult objects from all sources
    """

    def search_single_source(agent_type: str) -> List[SearchResult]:
        """Helper function to search a single source"""
        try:
            response = web_agent.search_and_format(query, agent_type)
            return response.results
        except Exception as e:
            print(f"Error searching {agent_type}: {str(e)}")
            return []

    # Create thread pool for concurrent searches
    with ThreadPoolExecutor() as executor:
        # Create tasks for each web source
        loop = asyncio.get_event_loop()
        tasks = []
        for source in web_sources:
            # Create partial function with the source
            search_func = partial(search_single_source, source)
            # Create task for concurrent execution
            task = loop.run_in_executor(executor, search_func)
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)

    # Flatten results from all sources
    all_results: List[SearchResult] = []
    for source_results in results:
        all_results.extend(source_results)

    print(f"Web results: {all_results}")
    print(f"Query: {query}")
    print(f"Sources: {web_sources}")
    print(f"Agent: {web_agent}")
    return all_results
