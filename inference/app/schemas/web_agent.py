from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, TypedDict


class AgentType(Enum):
    WEB = "web"
    YOUTUBE = "youtube"
    REDDIT = "reddit"
    GITHUB = "github"
    ARXIV = "arxiv"
    IMAGES = "images"


class SearchResult(TypedDict):
    title: str
    url: str
    content: Optional[str]
    additional_info: Dict[str, any]


class ReRankedWebSearchResult(SearchResult):
    score: float


@dataclass
class AgentResponse:
    query: str
    agent_type: AgentType
    results: List[SearchResult]
    formatted_prompt: str


class SearxngSearchOptions(TypedDict, total=False):
    categories: List[str]
    engines: List[str]
    language: str
    pageno: int


class SearxngSearchResult(TypedDict, total=False):
    title: str
    url: str
    img_src: Optional[str]
    thumbnail_src: Optional[str]
    thumbnail: Optional[str]
    content: Optional[str]
    author: Optional[str]
    iframe_src: Optional[str]


@dataclass
class SearchResponse:
    results: List[SearxngSearchResult]
    suggestions: List[str]
