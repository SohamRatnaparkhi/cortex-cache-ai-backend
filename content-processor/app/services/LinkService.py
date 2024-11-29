from typing import Optional

from app.core.agents import LinkAgents
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import (GitSpecificMd, Metadata, TextSpecificMd,
                                  YouTubeSpecificMd)
from app.utils.app_logger_config import logging


async def get_code_from_git_repo(repo_url: str, md: Metadata[GitSpecificMd]) -> AgentResponse:
    """
    Retrieve and process code from a Git repository.

    This function creates a GitAgent to fetch and process the contents of a Git repository.

    Args:
        repo_url (str): The URL of the Git repository to process.
        md (Metadata[GitSpecificMd]): Metadata specific to Git repositories.

    Returns:
        AgentResponse: The processed media content from the Git repository.

    Raises:
        ValueError: If code extraction from the repository fails.
        RuntimeError: If there's an error processing the Git repository.

    Example:
        repo_url = "https://github.com/username/repo.git"
        git_md = Metadata[GitSpecificMd](...)
        result = get_code_from_git_repo(repo_url, git_md)
    """
    git_agent = LinkAgents.GitAgent(repo_url, md)
    return await git_agent.process_media()


async def get_youtube_video_transcript(video_url: str, md: Metadata[YouTubeSpecificMd]) -> Optional[AgentResponse]:
    """
    Retrieve and process the transcript of a YouTube video.

    Args:
        video_url (str): The URL of the YouTube video to process.  
        md (Metadata[YouTubeSpecificMd]): Metadata specific to YouTube videos.

    Returns:
        Optional[AgentResponse]: The processed transcript or None if processing fails.

    Raises:
        ValueError: If video_url is invalid/empty
    """
    if not video_url:
        raise ValueError("Video URL cannot be empty")

    try:
        youtube_agent = LinkAgents.YoutubeAgent(resource_link=video_url, md=md)
        return await youtube_agent.process_media()

    except ValueError as ve:
        logging.error(
            f"Invalid YouTube URL or transcript unavailable: {str(ve)}")
        return None

    except Exception as e:
        logging.error(f"Error processing YouTube video {video_url}: {str(e)}")
        return None


async def get_web_scraped_data(url: str, md: Metadata[TextSpecificMd]) -> AgentResponse:
    """
    Retrieve and process data from a web page.

    This function creates a WebScrapingAgent to fetch and process the content of a web page.

    Args:
        url (str): The URL of the web page to process.
        md (Metadata[MediaSpecificMd]): Metadata specific to web pages.

    Returns:
        AgentResponse: The processed media content from the web page.

    Raises:
        ValueError: If data extraction from the web page fails.
        Exception: If there's an error processing the web page.

    Example:
        url = "https://example.com"
        web_md = Metadata[MediaSpecificMd](...)
        result = get_web_scraped_data(url, web_md)
    """
    web_agent = LinkAgents.WebAgent(resource_link=url, md=md)
    return await web_agent.process_media()
