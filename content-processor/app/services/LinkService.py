from app.core.agents import LinkAgents
from app.schemas.Common import AgentResponseWrapper
from app.schemas.Metadata import Metadata


def get_code_from_git_repo(repo_url: str) -> dict:
    git_agent = LinkAgents.GitAgent(repo_url)
    return git_agent.process_media()

def get_youtube_video_transcript(video_url: str, md: Metadata) -> AgentResponseWrapper:
    resource_link = video_url

    youtube_agent = LinkAgents.YoutubeAgent(
        resource_link=resource_link,
        md=md
    )
    # youtube_agent = LinkAgents.YoutubeAgent(video_url)

    print("Out from here 1")
    return youtube_agent.process_media()
