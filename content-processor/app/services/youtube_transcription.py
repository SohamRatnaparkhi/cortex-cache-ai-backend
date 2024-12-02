from typing import Dict, List, Tuple

import requests
import tiktoken
from youtube_transcript_api import YouTubeTranscriptApi

from app.utils.proxy import get_random_proxy


class TranscriptChunker:
    def __init__(
        self,
        max_tokens: int = 1000,
        min_tokens: int = 100,
        overlap_tokens: int = 50,
        model: str = "text-embedding-ada-002"
    ):
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.overlap_tokens = overlap_tokens
        self.tokenizer = tiktoken.encoding_for_model(model)

    def extract_video_id(self, video_url: str) -> str:
        """Extract video ID from various YouTube URL formats"""
        if '/watch?v=' in video_url:
            return video_url.split('/watch?v=')[1].split('&')[0]
        elif 'youtu.be/' in video_url:
            return video_url.split('youtu.be/')[1].split('?')[0]
        return video_url.split('/')[-1].split('?')[0]

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def create_chunks_from_transcript(self, transcript: List[Dict]) -> List[Dict]:
        """Create chunks from transcript while maintaining token limits"""
        chunks = []
        current_chunk = {
            'text': '',
            'start_time': transcript[0]['start'],
            'end_time': transcript[0]['start'],
            'token_count': 0
        }

        overlap_buffer = []
        overlap_token_count = 0

        for entry in transcript:
            text = entry['text'].strip()
            entry_tokens = self.count_tokens(text)

            if current_chunk['token_count'] + entry_tokens > self.max_tokens and current_chunk['token_count'] >= self.min_tokens:
                chunks.append(current_chunk)

                overlap_text = ' '.join([e['text'].strip()
                                        for e in overlap_buffer])
                current_chunk = {
                    'text': overlap_text,
                    'start_time': overlap_buffer[0]['start'] if overlap_buffer else entry['start'],
                    'end_time': entry['start'] + entry['duration'],
                    'token_count': overlap_token_count
                }

                overlap_buffer = overlap_buffer[-3:] if overlap_buffer else []
                overlap_token_count = sum(self.count_tokens(
                    e['text'].strip()) for e in overlap_buffer)

            current_chunk['text'] += f" {text}" if current_chunk['text'] else text
            current_chunk['end_time'] = entry['start'] + entry['duration']
            current_chunk['token_count'] = self.count_tokens(
                current_chunk['text'])

            overlap_buffer.append(entry)
            if len(overlap_buffer) > 5:
                removed_entry = overlap_buffer.pop(0)
                overlap_token_count -= self.count_tokens(
                    removed_entry['text'].strip())

        if current_chunk['text'] and current_chunk['token_count'] >= self.min_tokens:
            chunks.append(current_chunk)

        return chunks

    async def process_video(self, video_url: str, api_url: str) -> Tuple[List[Dict], str, str, str, str]:
        """
        Process video and return chunks with metadata
        Returns: (chunks, video_title, video_description, author, channel_name)
        """
        try:
            video_id = self.extract_video_id(video_url)
            print("Extracted video ID:", video_id)
            # Get video metadata
            response = requests.get(f"{api_url}{video_url}")
            video_title = "Untitled"
            video_desc = ""
            author = "Unknown"
            channel_name = "Unknown"
            print(response)
            if response.status_code == 200:
                data = response.json()
                video_title = data.get("title", "Untitled")
                video_desc = data.get("description", "")
                author = data.get("author_name", "Unknown")
                channel_name = data.get("author_url", "Unknown").split('/')[-1]

            # Get transcript
            proxyIp = get_random_proxy()
            print(f"Using proxy: {proxyIp}")
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id, proxies={
                    "https": proxyIp,
                    "http": proxyIp
                })

            # Create chunks
            chunks = self.create_chunks_from_transcript(transcript)

            print(f"Extracted {len(chunks)} chunks from video transcript")

            return chunks, video_title, video_desc, author, channel_name

        except Exception as e:
            raise Exception(
                f"Error processing YouTube video in chunker: {str(e)}")
