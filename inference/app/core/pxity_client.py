import re
from typing import Dict, List

from openai import AsyncOpenAI


class BaseAgent:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(
            api_key=api_key, base_url="https://api.perplexity.ai")
        self.model = "llama-3.1-sonar-large-128k-online"

    async def _get_response(self, messages: List[Dict[str, str]]):
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return self._parse_response(response)

    def _parse_response(self, response) -> Dict[str, List[Dict[str, str]]]:
        content = response.choices[0].message.content
        citations = response.citations

        # Extract cited text and map to URLs
        results = []
        citation_pattern = r'(.*?)\[(\d+)\]'
        matches = re.finditer(citation_pattern, content)

        for match in matches:
            text, citation_num = match.groups()
            citation_idx = int(citation_num) - 1
            if citation_idx < len(citations):
                results.append({
                    "content": text.strip(),
                    "citation_url": citations[citation_idx]
                })
        print(results)
        return {"results": results}


class WebAgent(BaseAgent):
    def __init__(self, api_key: str):
        super().__init__(api_key)

    async def search(self, query: str) -> Dict[str, List[Dict[str, str]]]:
        system_prompt = (
            "You are a web search assistant. Focus on finding relevant web "
            "pages and articles. Prioritize results from reputable sources."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        return await self._get_response(messages)


class ResearchAgent(BaseAgent):
    def __init__(self, api_key: str, focus: str = "arxiv"):
        super().__init__(api_key)
        self.focus = focus

    async def search(self, query: str) -> Dict[str, List[Dict[str, str]]]:
        system_prompt = (
            f"You are a research assistant focused on {self.focus}. "
            f"Prioritize results from {self.focus} and academic sources."
            "Provide detailed technical information with citations."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        return await self._get_response(messages)


class CodeAgent(BaseAgent):
    async def search(self, query: str) -> Dict[str, List[Dict[str, str]]]:
        system_prompt = (
            "You are a coding assistant. Focus on code repositories, "
            "documentation, and programming resources. Prioritize results "
            "from GitHub, GitLab, and official documentation."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        return await self._get_response(messages)


class VideoAgent(BaseAgent):
    async def search(self, query: str) -> Dict[str, List[Dict[str, str]]]:
        system_prompt = (
            "You are a video content assistant. Focus on finding relevant "
            "video content and tutorials. Prioritize results from YouTube "
            "and other video platforms."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        return await self._get_response(messages)


class RedditAgent(BaseAgent):
    async def search(self, query: str) -> Dict[str, List[Dict[str, str]]]:
        system_prompt = (
            "You are a Reddit assistant. Focus on finding relevant "
            "subreddits and posts. Prioritize results from Reddit."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        return await self._get_response(messages)
