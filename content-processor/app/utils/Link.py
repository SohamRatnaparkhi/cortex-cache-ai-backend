import json
import os
from typing import Union

import requests
from git import Repo
from pytubefix import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import JSONFormatter

from app.schemas.Common import AgentResponse
from app.schemas.Metadata import GitSpecificMd, Metadata
from app.utils.AV import (extract_audio_from_video,
                          process_audio_for_transcription)
from app.utils.File import get_every_file_content_in_folder


def clone_git_repo(repo_url: str) -> Union[bool, str]:
    """
    Clone a git repository to a local directory.

    Args:
        repo_url (str): The URL of the git repository to clone.

    Returns:
        Union[bool, str]: A tuple containing a boolean indicating success and either the path to the cloned repo or an error message.
    """
    try:
        repo_name = repo_url.split('/')[-1]
        path = f'./tmp/git_repo/{repo_name}'

        if os.path.exists(path):
            os.system(f"rm -rf {path}")
        os.makedirs(path, exist_ok=True)
        Repo.clone_from(repo_url, path)
        return True, path
    except Exception as e:
        return False, f"Error cloning {repo_url}: {str(e)}"

def extract_code_from_repo(repo_url: str, metadata: Metadata[GitSpecificMd]) -> AgentResponse:
    """
    Extract code from a git repository.

    Args:
        repo_url (str): The URL of the git repository.

    Returns:
        Union[bool, dict]: A tuple containing a boolean indicating success and either the extracted code content or an error message.
    """
    success, path = clone_git_repo(repo_url)
    if not success:
        return AgentResponse(
            content="",
            chunks=[],
            metadata=[]
        )
    content = get_every_file_content_in_folder(path, is_code=True, repo_link=repo_url, md=metadata)
    os.system(f"rm -rf ./tmp")
    return content

def extract_youtube_transcript(video_id: str) -> str:
    """
    Extract and format the transcript of a YouTube video.

    Args:
        video_id (str): The ID of the YouTube video.

    Returns:
        str: The formatted transcript of the video.
    """
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    tr = next(iter(transcript_list))

    formatter = JSONFormatter()
    json_formatted = formatter.format_transcript(tr.fetch())
    transcript = ""
    for group in json.loads(json_formatted):
        text = group["text"]
        for i in range(1, len(text)):
            if text[i].isupper():
                text = text[:i] + ". " + text[i:]
        transcript += " " + text
    return transcript.strip()

def extract_transcript_from_youtube(video_url: str) -> Union[str, str, str]:
    """
    Extract transcript, title, and description from a YouTube video.

    Args:
        video_url (str): The URL of the YouTube video.

    Returns:
        Union[str, str, str]: A tuple containing the transcript, video title, and video description.
        If an error occurs, returns a dictionary with an 'error' key.
    """
    SAVE_PATH = "./tmp"
    try:
        yt = YouTube(video_url)
        video_title = yt.title
        video_description = yt.description

        ys = yt.streams.get_lowest_resolution()
        ys.download(output_path=SAVE_PATH)
        video_file = os.path.join(SAVE_PATH, yt.title + ".mp4")

        with open(video_file, 'rb') as f:
            video_bytes = f.read()
        audio_content = extract_audio_from_video(video_bytes)
        transcript = process_audio_for_transcription(audio_content=audio_content)

        os.remove(video_file)

        if not transcript:
            raise ValueError("Failed to extract transcript from YouTube video")

        return transcript, video_title, video_description
    except Exception as e:
        return {"error": str(e)}
