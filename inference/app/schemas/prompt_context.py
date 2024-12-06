from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional, Union


class AgentType(Enum):
    DEFAULT = 'default'
    SOCIAL = 'social'
    CODE = 'code'


@dataclass
class PromptContext:
    original_query: str
    refined_query: str
    context: Optional[str]
    initial_answer: Optional[str]
    web_data: Optional[str] = None
    web_agents: Optional[List[str]] = None
    is_stream: bool = True
    use_memory: bool = True
    agent: str = 'default'
    total_memories: int = 0


class FrameworkType(Enum):
    CHAT_AND_MEMORY = "chat_and_memory"
    CHAT_AND_WEB = "chat_and_web"
    MEMORY_AND_WEB = "memory_and_web"
    MEMORY_ONLY = "memory_only"
    WEB_ONLY = "web_only"
    CHAT_ONLY = "chat_only"
    NO_CONTEXT = "no_context"
