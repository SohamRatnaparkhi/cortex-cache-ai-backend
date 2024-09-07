from pydantic import BaseModel

from app.schemas.Metadata import Metadata


class YoutubeLinkRequest(BaseModel):
    # video_id: str
    video_url: str
    metadata: Metadata 

class GitLinkRequest(BaseModel):
    repo_url: str
    metadata: Metadata