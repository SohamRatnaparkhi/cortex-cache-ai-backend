import os
from abc import ABC, abstractmethod
from typing import Any, Dict

import requests
from app.core.jina_ai import use_jina
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import Metadata, YouTubeSpecificMd
from app.utils.Link import (extract_code_from_repo,
                            extract_transcript_from_youtube)
from dotenv import load_dotenv

load_dotenv()

class LinkAgent(ABC):
    def __init__(self, resource_link: str, md: Metadata) -> None:
        super().__init__()
        self.resource_link = resource_link
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
        self.md = md

    @abstractmethod
    def process_media(self) -> Dict[str, Any]:
        pass


class GitAgent(LinkAgent):
    def process_media(self) -> Dict[str, Any]:
        try:
            repo_url = self.resource_link
            success, code = extract_code_from_repo(repo_url=repo_url)
            if not success:
                raise ValueError(f"Failed to extract code from repository: {code}")
            return {"code": code}
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise RuntimeError(f"Error processing Git repository: {str(e)}")


class YoutubeAgent(LinkAgent):
    def process_media(self) -> AgentResponse:
        try:
            api_url = os.getenv("YOUTUBE_NO_EMBED_API_URL")
            video_url = self.resource_link
            video_id = video_url.split("/")[-1]
            if '?' in video_id:
                video_id = video_id.split('?')[0]
            # print("video_id", video_id)
            transcript, video_title, video_desc = extract_transcript_from_youtube(video_url)
            # print(transcript)
            self.md.title = video_title
            self.md.description = video_desc
            if not transcript:
                raise ValueError("Failed to extract transcript from YouTube video")
            chunks = use_jina.segment_data(transcript)
            print('chunking done')
            # print(chunks)
            if chunks is not None and "chunks" in chunks.keys():
                chunks = chunks["chunks"]
            author = None
            channel_name = None
            response = requests.get(f"{api_url}{video_url}")
            if response.status_code == 200:
                data = response.json()
                author = data.get("author_name")
                channel_name = data.get("author_url").split('/')[-1]
            
            if author is None:
                author = "Unknown"
            if channel_name is None:
                channel_name = "Unknown"
            # print(author, channel_name)
            # print(self.md)
            meta_chunks = []
            for i in range(len(chunks)):
                ymd = YouTubeSpecificMd(
                    video_id=video_id,
                    chunk_id=f'{i}',
                    channel_name=channel_name,
                    author_name=author,
                )
                self.md.specific_desc = ymd
                meta_chunks.append(self.md)
            return AgentResponse(
                chunks=chunks,
                metadata=meta_chunks,
                transcript=transcript
            )
        except Exception as e:
            return {"error": f"Error processing YouTube video: {str(e)}"}
