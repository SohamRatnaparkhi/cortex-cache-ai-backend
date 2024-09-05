from typing import Optional, Union

from pydantic import BaseModel


class YouTubeSpecificMd(BaseModel):
    video_id: str
    duration: str
    channel_name: str


class GitSpecificMd(BaseModel):
    repo_name: str
    repo_creator_name: str
    file_name: str
    programming_language: str
    chunk_type: str


class MediaSpecificMd(BaseModel):
    duration: float
    speaker: Optional[str] = None


class ImageSpecificMd(BaseModel):
    width: int
    height: int
    format: str


class TextSpecificMd(BaseModel):
    word_count: int
    reading_time: float  # in minutes
    tags: list[str]


class MindMapSpecificMd(BaseModel):
    memory_count: int
    central_topic: str
    subtopics: list[str]


class Metadata(BaseModel):
    id: str
    type: str  # "memory" or "mind_map"
    title: str
    description: str
    created_at: str
    last_updated: str
    user_id: str
    mem_id: str
    tags: list[str]
    source: str
    language: str
    content_hash: str
    specific_desc: Union[YouTubeSpecificMd, GitSpecificMd, MediaSpecificMd, ImageSpecificMd, TextSpecificMd, MindMapSpecificMd]
    ai_summary: Optional[str] = None
    ai_insights: Optional[str] = None
    related_memories: Optional[list[str]] = None
