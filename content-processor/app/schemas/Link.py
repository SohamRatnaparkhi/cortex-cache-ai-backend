from pydantic import BaseModel

from app.schemas.Metadata import (GitSpecificMd, Metadata, TextSpecificMd,
                                  YouTubeSpecificMd)


class YoutubeLinkRequest(BaseModel):
    # video_id: str
    video_url: str
    metadata: Metadata[YouTubeSpecificMd]


class GitLinkRequest(BaseModel):
    repo_url: str
    metadata: Metadata[GitSpecificMd]


class WebLinkRequest(BaseModel):
    url: str
    metadata: Metadata[TextSpecificMd]
