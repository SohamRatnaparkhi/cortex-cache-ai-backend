import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, TypeVar

import requests
from dotenv import load_dotenv
from git import Union

from app.core.jina_ai import use_jina
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import GitSpecificMd, Metadata, YouTubeSpecificMd
from app.utils.Link import (extract_code_from_repo,
                            extract_transcript_from_youtube)

load_dotenv()

T = TypeVar('T', YouTubeSpecificMd, GitSpecificMd)

class LinkAgent(ABC, Generic[T]):
    """
    Abstract base class for link agents that process different types of media.

    Attributes:
        resource_link (str): The URL of the resource to process.
        md (Metadata[T]): Metadata associated with the resource.
    """

    def __init__(self, resource_link: str, md: Metadata[T]) -> None:
        super().__init__()
        self.resource_link = resource_link
        self.md = md
        self.user_id = md.user_id
        self.mem_id = md.mem_id
        self.title = md.title
        self.created_at = md.created_at
        self.last_updated = md.last_updated
        self.tags = md.tags
        self.source = md.source
        self.language = md.language
        self.type = md.type
        self.description = md.description

    @abstractmethod
    def process_media(self) -> AgentResponse:
        """
        Abstract method to process the media.

        Returns:
            AgentResponse: The processed media content.
        """
        pass


class GitAgent(LinkAgent[GitSpecificMd]):
    """
    Agent for processing Git repositories.
    """

    def process_media(self) -> AgentResponse:
        """
        Process a Git repository and extract its code into chunks with metadata.

        Returns:
            AgentResponse: An object containing the extracted code chunks, metadata, and full content.

        Raises:
            ValueError: If code extraction from the repository fails.
            RuntimeError: If there's an error processing the Git repository.
        """
        try:
            repo_url = self.resource_link
            code = extract_code_from_repo(repo_url=repo_url, metadata=self.md)
            
            chunks = code.chunks
            meta_chunks = code.metadata
            content = code.transcript

            return AgentResponse(
                chunks=chunks,
                metadata=meta_chunks,
                transcript=content
            )
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise RuntimeError(f"Error processing Git repository: {str(e)}")


class YoutubeAgent(LinkAgent[YouTubeSpecificMd]):
    """
    Agent for processing YouTube videos.
    """

    def process_media(self) -> AgentResponse:
        """
        Process a YouTube video, extract its transcript, and segment it into chunks.

        This method performs the following steps:
        1. Extracts the video ID from the URL.
        2. Retrieves the video transcript and metadata.
        3. Segments the transcript into chunks using Jina AI.
        4. Fetches additional video metadata (author and channel name).
        5. Creates metadata for each chunk.

        Returns:
            AgentResponse: An object containing the segmented chunks, metadata, and full transcript.

        Raises:
            ValueError: If the transcript extraction fails.
            Exception: If there's any error during the processing of the YouTube video.
        """
        try:
            api_url = os.getenv("YOUTUBE_NO_EMBED_API_URL")
            video_url = self.resource_link
            video_id = video_url.split("/")[-1]
            if '?' in video_id:
                video_id = video_id.split('?')[0]

            transcript, video_title, video_desc = extract_transcript_from_youtube(video_url)
            self.md.title = video_title
            self.md.description = video_desc
            if not transcript:
                raise ValueError("Failed to extract transcript from YouTube video")
            chunks = use_jina.segment_data(transcript)
            if chunks is not None and "chunks" in chunks.keys():
                chunks = chunks["chunks"]
            author = None
            channel_name = None
            response = requests.get(f"{api_url}{video_url}")
            if response.status_code == 200:
                data = response.json()
                author = data.get("author_name")
                channel_name = data.get("author_url").split('/')[-1]
            
            author = author or "Unknown"
            channel_name = channel_name or "Unknown"

            meta_chunks = []
            for i in range(len(chunks)):
                ymd = YouTubeSpecificMd(
                    video_id=video_id,
                    chunk_id=f'{i}',
                    channel_name=channel_name,
                    author_name=author,
                )
                md_copy = self.md.model_copy()
                md_copy.specific_desc = ymd
                meta_chunks.append(md_copy)
            return AgentResponse(
                chunks=chunks,
                metadata=meta_chunks,
                transcript=transcript
            )
        except Exception as e:
            raise Exception(f"Error processing YouTube video: {str(e)}")
