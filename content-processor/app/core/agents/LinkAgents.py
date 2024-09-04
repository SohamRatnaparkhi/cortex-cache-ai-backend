from abc import ABC, abstractmethod

from app.utils.Link import extract_code_from_repo, extract_youtube_transcript


class LinkAgent(ABC):
    def __init__(self, resource_link) -> None:
        super().__init__()
        self.resource_link = resource_link

    @abstractmethod
    async def process_media(self) -> dict:
        pass


class GitAgent(LinkAgent):
    def process_media(self):
        repo_url = self.resource_link
        code = extract_code_from_repo(repo_url=repo_url)
        return {"code": code}
    

class YoutubeAgent(LinkAgent):
    def process_media(self):
        video_url = self.resource_link
        video_id = video_url.split("/")[-1]
        if '?' in video_id:
            video_id = video_id.split('?')[0]
        transcript = extract_youtube_transcript(video_id)
        print("Out after transcript")
        return {"transcript": transcript}
