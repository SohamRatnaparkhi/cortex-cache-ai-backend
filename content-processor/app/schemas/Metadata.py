from typing import Generic, Optional, TypeVar, Union

from pydantic import BaseModel

# Specific metadata models for different content types

class YouTubeSpecificMd(BaseModel):
    video_id: str
    channel_name: str
    author_name: str
    chunk_id: str

class GitSpecificMd(BaseModel):
    repo_name: str
    repo_creator_name: str
    file_name: str
    programming_language: str
    chunk_type: str
    chunk_id: str

class MediaSpecificMd(BaseModel):
    duration: float
    speaker: Optional[str] = None
    chunk_id: str

class ImageSpecificMd(BaseModel):
    width: int
    height: int
    format: str
    chunk_id: str

class TextSpecificMd(BaseModel):
    word_count: int
    reading_time: float  # in minutes
    tags: list[str]
    chunk_id: str

class MindMapSpecificMd(BaseModel):
    memory_count: int
    central_topic: str
    subtopics: list[str]
    chunk_id: str

T = TypeVar('T')

# Main Metadata model that includes common fields and specific metadata
class Metadata(BaseModel, Generic[T]):
    user_id: str
    mem_id: str
    title: str
    description: str
    created_at: str
    last_updated: str
    tags: list[str]
    source: str
    language: str
    type: str
    content_hash: Optional[str] = None
    specific_desc: T
    ai_summary: Optional[str] = None
    ai_insights: Optional[str] = None
    related_memories: Optional[list[str]] = None

