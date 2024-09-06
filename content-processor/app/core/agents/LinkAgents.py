from abc import ABC, abstractmethod
from typing import Any, Dict

from app.core.jina_ai import use_jina
from app.utils.Link import extract_code_from_repo, extract_youtube_transcript


class LinkAgent(ABC):
    def __init__(self, resource_link: str) -> None:
        super().__init__()
        self.resource_link = resource_link

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
    def process_media(self) -> Dict[str, Any]:
        try:
            video_url = self.resource_link
            video_id = video_url.split("/")[-1]
            if '?' in video_id:
                video_id = video_id.split('?')[0]
            transcript = extract_youtube_transcript(video_id)
            if not transcript:
                raise ValueError("Failed to extract transcript from YouTube video")
            chunks = use_jina.segment_data(transcript)
            return {
                "transcript": transcript,
                "chunks": chunks['chunks']
            }
        except Exception as e:
            return {"error": f"Error processing YouTube video: {str(e)}"}
