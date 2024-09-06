import json
import os
from typing import Union

from git import Repo
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import JSONFormatter

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

def extract_youtube_transcript(video_id: str) -> dict:
    # print("In")
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    # print("out")
    # iterate over all available transcripts
    tr = None
    for transcript in transcript_list:
        print(transcript.fetch())
        tr = transcript.fetch()
        break

    formatter = JSONFormatter()

    # .format_transcript(transcript) turns the transcript into a JSON string.
    json_formatted = formatter.format_transcript(tr)
    transcript = ""
    for group in json.loads(json_formatted):
        # if first char is capital add a full stop
        if group["text"][0].isupper() and (len(group["text"][0]) == 1 and group["text"][0].isupper()) != 'I':
            transcript += ". " + group["text"]
        else:
            transcript += " " + group["text"]
    return transcript
