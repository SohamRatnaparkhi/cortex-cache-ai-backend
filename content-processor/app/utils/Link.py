import json
import os
from typing import Union

import requests
import yt_dlp
from git import Repo
from pytubefix import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import JSONFormatter

from app.utils.AV import (extract_audio_from_video,
                          process_audio_for_transcription)
from app.utils.File import get_every_file_content_in_folder


def clone_git_repo(repo_url: str) -> Union[bool, str]:
    try:
        repo_name = repo_url.split('/')[-1]
        path = f'./tmp/git_repo/{repo_name}'

        #check and delete folder at path if it exists
        if os.path.exists(path):
            os.system(f"rm -rf {path}")
        # create a folder at the path if it doesn't exist
        # print("Making dir")
        os.makedirs(path, exist_ok=True)
        # print("Clone started")
        Repo.clone_from(repo_url, path)
        # print(f"clone over at {path}")
        return True, path
    except Exception as e:
        # print(f"Error cloning {repo_url}: {str(e)}")
        return False, f"Error cloning {repo_url}: {str(e)}"


def extract_code_from_repo(repo_url: str) -> Union[bool, str]:
    success, path = clone_git_repo(repo_url)
    print(success, path)
    if not success:
        return success, path
    print("clone over")
    content = get_every_file_content_in_folder(path, is_code=True)
    # forcefully delete a directory
    os.system(f"rm -rf ./tmp")
    return True, content


def extract_youtube_transcript(video_id: str) -> str:
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    tr = None
    for transcript in transcript_list:
        tr = transcript.fetch()
        break

    formatter = JSONFormatter()
    json_formatted = formatter.format_transcript(tr)
    print(json_formatted)
    transcript = ""
    for group in json.loads(json_formatted):
        text = group["text"]
        # Add full stop and space before each capital letter (except first char)
        for i in range(1, len(text)):
            if text[i].isupper():
                text = text[:i] + ". " + text[i:]
        transcript += " " + text
    return transcript.strip()


def extract_transcript_from_youtube(video_url: str) -> Union[str, str, str]:
    # video_url = f"https://www.youtube.com/v={video_id}"
    SAVE_PATH = "./tmp"
    print("in here")
    try:
        # yt = YouTube(video_url)
        print("yt")
        # mp4_streams = yt.streams.filter(file_extension='mp4').all()
        # d_video = min(mp4_streams, key=lambda x: x.resolution)
        # d_video.download(output_path=SAVE_PATH)
        # yt.streams(progressive=True, file_extension='mp4').order_by(
        #     'resolution').asc().first().download(output_path=SAVE_PATH)
        yt = YouTube(video_url)
        video_title = yt.title
        video_description = yt.description

        print(yt.title)

        # ys = yt.streams.get_highest_resolution()
        ys = yt.streams.get_lowest_resolution()
        ys.download(output_path=SAVE_PATH)
        video_file = os.path.join(SAVE_PATH, yt.title + ".mp4")

        with open(video_file, 'rb') as f:
            video_bytes = f.read()
        audio_content = extract_audio_from_video(video_bytes)
        transcript = process_audio_for_transcription(
            audio_content=audio_content)

        os.remove(video_file)

        if not transcript:
            raise ValueError("Failed to extract transcript from YouTube video")

        return transcript, video_title, video_description
    except Exception as e:
        print(e)
        return {
            "error": str(e)
        }
