from typing import List, Tuple, Union

from app.core import voyage_client
from app.core.content_fetcher import ContentFetcher
from app.schemas.web_agent import (AgentResponse, AgentType,
                                   ReRankedWebSearchResult, SearchResult)


class WebAgent:
    def __init__(self, search_function):
        self.search = search_function
        self.content_fetcher = ContentFetcher()
        self.engine_mappings = {
            AgentType.WEB: ["google", "bing", "duckduckgo"],
            AgentType.YOUTUBE: ["youtube"],
            AgentType.REDDIT: ["reddit"],
            AgentType.GITHUB: ["github"],
            AgentType.ARXIV: ["arxiv"],
            AgentType.IMAGES: ["bing images", "google images"],
        }

        self.formatters = {
            AgentType.WEB: self._format_web_results,
            AgentType.YOUTUBE: self._format_youtube_results,
            AgentType.REDDIT: self._format_reddit_results,
            AgentType.GITHUB: self._format_github_results,
            AgentType.ARXIV: self._format_arxiv_results,
            AgentType.IMAGES: self._format_image_results,
        }

    def _get_search_options(self, agent_type: AgentType) -> dict:
        """Get search options for specific agent type."""
        base_opts = {
            "format": "json"
        }

        if agent_type in self.engine_mappings:
            base_opts["engines"] = self.engine_mappings[agent_type]

        # Add type-specific options
        if agent_type == AgentType.IMAGES:
            base_opts["categories"] = ["images"]
        elif agent_type == AgentType.YOUTUBE:
            base_opts["categories"] = ["videos"]

        return base_opts

    def _format_web_results(self, results: List[dict]) -> Tuple[List[SearchResult], str]:
        formatted_results = []
        context_parts = [
            "Here are the most relevant web search results with full content:\n"]

        for i, result in enumerate(results, 1):
            try:
                # Validate required fields
                url = result.get("url", "")
                if not url:
                    print(f"Warning: Missing URL for result {i}")
                    continue

                # Fetch full content with error handling
                try:
                    full_content = self.content_fetcher.fetch_web_content(url)
                except Exception as e:
                    print(f"Error fetching content from {url}: {str(e)}")
                    full_content = ""

                # Combine existing content with full content, handling None values
                base_content = result.get("content", "") or ""
                combined_content = base_content
                if full_content:
                    combined_content = f"{base_content}\n{full_content}" if base_content else full_content

                # Create SearchResult object
                formatted_result = SearchResult(
                    title=combined_content.split(
                        '\n')[0][0:30] if combined_content else base_content[0:30],
                    url=url,
                    source="web",
                    content=combined_content,
                    additional_info={}
                )

                formatted_results.append(formatted_result)

                # Access attributes correctly using dot notation since SearchResult is a dataclass
                # context_parts.append(f"{i}. Title: {formatted_result.title}")
                context_parts.append(f"   URL: {formatted_result.url}")
                if formatted_result.content:
                    # Split content into chunks to avoid extremely long lines
                    content_chunks = formatted_result.content.split('\n')
                    for chunk in content_chunks:
                        if chunk.strip():
                            context_parts.append(
                                f"   Content: {chunk.strip()}")
                context_parts.append("")

            except Exception as e:
                print(f"Error processing result{i}: {str(e)}")
                continue

        if not formatted_results:
            return [], "No results could be formatted successfully."

        return formatted_results, "\n".join(context_parts)

    def _format_youtube_results(self, results: List[dict]) -> Tuple[List[SearchResult], str]:
        formatted_results = []
        context_parts = [
            "Here are the most relevant YouTube videos with full descriptions:\n"]

        for i, result in enumerate(results, 1):
            # Fetch full description

            formatted_result = SearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                content=result.get("content", ""),
                source="youtube",
                additional_info={
                    "duration": result.get("duration", ""),
                    "views": result.get("views", ""),
                    "channel": result.get("author", "")
                }
            )
            formatted_results.append(formatted_result)

            context_parts.append(f"{i}. Title: {formatted_result['title']}")
            context_parts.append(
                f"   Channel: {formatted_result['additional_info']['channel']}")
            context_parts.append(f"   URL: {formatted_result['url']}")
            if formatted_result['content']:
                context_parts.append(
                    f"   Description: {formatted_result['content']}")
            context_parts.append("")

        return formatted_results, "\n".join(context_parts)

    def _format_reddit_results(self, results: List[dict]) -> Tuple[List[SearchResult], str]:
        formatted_results = []
        context_parts = [
            "Here are the most relevant Reddit posts with full content and top comments:\n"]

        for i, result in enumerate(results, 1):
            # Fetch full content
            full_content = self.content_fetcher.fetch_reddit_content(
                result.get("url", ""))

            formatted_result = SearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                content=result.get("content", "") + full_content,
                source="reddit",
                additional_info={
                    "subreddit": result.get("subreddit", ""),
                    "score": result.get("score", ""),
                    "comments": result.get("comments", "")
                }
            )
            formatted_results.append(formatted_result)

            context_parts.append(f"{i}. Title: {formatted_result['title']}")
            context_parts.append(
                f"   Subreddit: r/{formatted_result['additional_info']['subreddit']}")
            context_parts.append(f"   URL: {formatted_result['url']}")
            if formatted_result['content']:
                context_parts.append(
                    f"   Content: {formatted_result['content']}")
            context_parts.append("")

        return formatted_results, "\n".join(context_parts)

    def _format_github_results(self, results: List[dict]) -> Tuple[List[SearchResult], str]:
        formatted_results = []
        context_parts = [
            "Here are the most relevant GitHub repositories with README content:\n"]

        for i, result in enumerate(results, 1):
            # Fetch README content
            readme_content = self.content_fetcher.fetch_github_readme(
                result.get("url", ""))

            formatted_result = SearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                content=result.get("content", "") + readme_content,
                source="github",
                additional_info={
                    "language": result.get("language", ""),
                    "stars": result.get("stars", ""),
                    "forks": result.get("forks", "")
                }
            )
            formatted_results.append(formatted_result)

            context_parts.append(
                f"{i}. Repository: {formatted_result['title']}")
            context_parts.append(f"   URL: {formatted_result['url']}")
            if formatted_result['content']:
                context_parts.append(
                    f"   README: {formatted_result['content']}")
            context_parts.append("")

        return formatted_results, "\n".join(context_parts)

    def _format_arxiv_results(self, results: List[dict]) -> Tuple[List[SearchResult], str]:
        formatted_results = []
        context_parts = [
            "Here are the most relevant academic papers from arXiv:\n"]

        for i, result in enumerate(results, 1):
            formatted_result = SearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                content=result.get("content", ""),
                source="arxiv",
                additional_info={
                    "authors": result.get("author", ""),
                    "published_date": result.get("publishedDate", ""),
                    "pdf_url": result.get("pdf_url", "")
                }
            )
            formatted_results.append(formatted_result)

            context_parts.append(f"{i}. Title: {formatted_result['title']}")
            context_parts.append(
                f"   Authors: {formatted_result['additional_info']['authors']}")
            context_parts.append(
                f"   Published: {formatted_result['additional_info']['published_date']}")
            context_parts.append(f"   URL: {formatted_result['url']}")
            if formatted_result['content']:
                context_parts.append(
                    f"   Abstract: {formatted_result['content']}")
            context_parts.append("")

        return formatted_results, "\n".join(context_parts)

    def _format_image_results(self, results: List[dict]) -> Tuple[List[SearchResult], str]:
        formatted_results = []
        context_parts = ["Here are the most relevant images:\n"]

        for i, result in enumerate(results, 1):
            formatted_result = SearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                content=result.get("content", ""),
                source="images",
                additional_info={
                    "img_src": result.get("img_src", ""),
                    "thumbnail": result.get("thumbnail", ""),
                    "source": result.get("source", "")
                }
            )
            formatted_results.append(formatted_result)

            context_parts.append(f"{i}. Title: {formatted_result['title']}")
            context_parts.append(f"   Source: {formatted_result['url']}")
            context_parts.append(
                f"   Image URL: {formatted_result['additional_info']['img_src']}")
            context_parts.append("")

        return formatted_results, "\n".join(context_parts)

    def search_and_format(self, query: str, agent_type: Union[AgentType, str]) -> AgentResponse:
        """
        Search using specified agent type and format results for LLM.

        Args:
            query: Search query
            agent_type: Type of agent to use

        Returns:
            AgentResponse object containing results and formatted prompt for LLM
        """
        # Convert string to AgentType if needed
        if isinstance(agent_type, str):
            agent_type = AgentType(agent_type.lower())

        print("Searching for:", query, agent_type)

        # Get search options for this agent type
        search_opts = self._get_search_options(agent_type)

        # Perform search
        search_response = self.search(query, search_opts)

        # Format results using appropriate formatter
        formatter = self.formatters.get(agent_type, self._format_web_results)
        formatted_results, formatted_prompt = formatter(
            search_response.results)

        return AgentResponse(
            query=query,
            agent_type=agent_type,
            results=formatted_results,
            formatted_prompt=formatted_prompt
        )

    def search_and_rerank(self, query: str, agent_type: Union[AgentType, str], limit=10) -> List[ReRankedWebSearchResult] | None:
        """
        Search using specified agent type, rerank results, and format for LLM.

        Args:
            query: Search query
            agent_type: Type of agent to use

        Returns:
            AgentResponse object containing results and formatted prompt for LLM
        """
        # Perform initial search
        response = self.search_and_format(query, agent_type)
        results = response.results[0: limit]

        # Rerank results using voyage
        re_ranked_results = voyage_client.re_rank_web_data(
            results, k=5, query=query)
        return re_ranked_results
