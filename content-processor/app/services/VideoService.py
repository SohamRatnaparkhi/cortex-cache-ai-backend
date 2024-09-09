from app.core.agents.MediaAgent import VideoAgent
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import MediaSpecificMd, Metadata


def get_video_transcript(s3_bucket_key: str, md: Metadata[MediaSpecificMd]) -> AgentResponse:
    video_agent = VideoAgent(s3_media_key=s3_bucket_key, md=md)
    return video_agent.process_media()