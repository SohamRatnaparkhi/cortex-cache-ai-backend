from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

# Specific metadata models for different content types


class YouTubeSpecificMd(BaseModel):
    video_id: str
    channel_name: str
    author_name: str
    chunk_id: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class GitSpecificMd(BaseModel):
    repo_name: str
    repo_creator_name: str
    file_name: str
    programming_language: str
    chunk_type: str
    chunk_id: str


class MediaSpecificMd(BaseModel):
    type: str
    chunk_id: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class ImageSpecificMd(BaseModel):
    width: int
    height: int
    format: str
    chunk_id: str


class TextSpecificMd(BaseModel):
    chunk_id: str
    url: str


class MindMapSpecificMd(BaseModel):
    memory_count: int
    central_topic: str
    subtopics: list[str]
    chunk_id: str


T = TypeVar('T')

# Main Metadata model that includes common fields and specific metadata


class Metadata(BaseModel, Generic[T]):
    user_id: str
    memId: str
    title: str
    description: str
    created_at: str
    last_updated: str
    tags: list[str]
    source: str
    language: str = "english"
    type: str
    content_hash: Optional[str] = None
    specific_desc: T
    ai_summary: Optional[str] = None
    ai_insights: Optional[str] = None
    related_memories: Optional[list[str]] = None
