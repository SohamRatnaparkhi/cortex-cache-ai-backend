import asyncio
import io
import os
from typing import Any, Dict, List, Tuple

import numpy as np
import openai
from dotenv import load_dotenv
from pydub import AudioSegment

from app.utils.language_codes import TO_LANGUAGE_CODE

client = openai.AsyncOpenAI()

if os.path.exists('.env'):
    load_dotenv()

TEMP_FOLDER_PATH = os.getenv("TEMP_FOLDER_PATH", "/tmp")
print(f"temporary folder path = {TEMP_FOLDER_PATH}")

os.makedirs(TEMP_FOLDER_PATH, exist_ok=True)


async def extract_audio_from_video(video_bytes: bytes) -> bytes:
    """Extract audio from video bytes and return audio content."""
    temp_video_path = os.path.join(
        TEMP_FOLDER_PATH, f"temp_video_{os.urandom(4).hex()}.mp4")

    try:
        # Ensure temp directory exists
        os.makedirs(os.path.dirname(temp_video_path), exist_ok=True)

        # Write video bytes to temporary file
        with open(temp_video_path, "wb") as temp_video:
            temp_video.write(video_bytes)

        # Extract audio
        video = AudioSegment.from_file(temp_video_path, format="mp4")
        audio_content = io.BytesIO()
        video.export(audio_content, format="wav")
        audio_content.seek(0)
        return audio_content.read()
    finally:
        if os.path.exists(temp_video_path):
            os.unlink(temp_video_path)


def safe_float_conversion(value: Any) -> float:
    """Converts a value to a regular float if it's a numpy float."""
    if isinstance(value, np.floating):
        return float(value)
    return value


async def transcribe_audio_chunk(
    chunk: AudioSegment,
    chunk_index: int,
    lang: str = "en"
) -> Tuple[str, List[Tuple[float, float, str]]]:
    """Transcribe a single audio chunk using OpenAI's Whisper API."""
    temp_chunk_path = os.path.join(
        TEMP_FOLDER_PATH,
        f"temp_chunk_{chunk_index}_{os.urandom(4).hex()}.wav"
    )

    try:
        # Ensure temp directory exists
        os.makedirs(os.path.dirname(temp_chunk_path), exist_ok=True)

        # Ensure correct format and export
        chunk = chunk.set_frame_rate(16000).set_channels(1)
        chunk.export(temp_chunk_path, format="wav")

        # Open the temporary file for the API request
        with open(temp_chunk_path, "rb") as audio_file:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=lang,
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"]
            )

        # Process timestamps from the response
        timestamps = []
        for segment in response.segments:
            start = float(segment.start)
            end = float(segment.end)
            text = segment.text
            timestamps.append((start, end, text))

        return response.text, timestamps

    except Exception as e:
        print(f"Error during chunk {chunk_index + 1} transcription: {str(e)}")
        return "", []

    finally:
        if os.path.exists(temp_chunk_path):
            os.unlink(temp_chunk_path)


async def process_audio_for_transcription(
    audio_content: bytes,
    max_concurrent: int = 4,
    language: str = "english"
) -> Tuple[str, List[Dict[str, Any]]]:
    """Process audio for transcription, dynamically splitting into chunks."""
    try:
        sound = AudioSegment.from_wav(io.BytesIO(audio_content))
        total_duration_ms = len(sound)

        # Dynamically calculate chunk size
        chunk_length_ms = max(min(total_duration_ms // 10, 600000), 60000)

        # Split into initial chunks
        initial_chunks = [
            sound[i:i + chunk_length_ms]
            for i in range(0, total_duration_ms, chunk_length_ms)
        ]

        # Merge small chunks with the previous one
        merged_chunks = []
        current_chunk = initial_chunks[0]
        for next_chunk in initial_chunks[1:]:
            if len(next_chunk) < 60000:  # If next chunk is less than 1 minute
                current_chunk += next_chunk
            else:
                merged_chunks.append(current_chunk)
                current_chunk = next_chunk
        merged_chunks.append(current_chunk)

        # Calculate chunk offsets
        chunk_offsets = [0]
        for i in range(len(merged_chunks) - 1):
            chunk_offsets.append(
                chunk_offsets[i] + len(merged_chunks[i]) / 1000)

        # Process chunks concurrently with rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)
        language_code = TO_LANGUAGE_CODE.get(language, "en")

        async def process_chunk(chunk, index):
            async with semaphore:
                return await transcribe_audio_chunk(chunk, index, language_code)

        # Create tasks for all chunks
        tasks = [
            process_chunk(chunk, i)
            for i, chunk in enumerate(merged_chunks)
        ]

        # Execute all tasks and gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        transcriptions = []
        all_timestamps = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Chunk {i + 1} generated an exception: {str(result)}")
                transcriptions.append("")
                continue

            text, timestamps = result
            transcriptions.append(text.strip())

            # Adjust timestamps with chunk offsets
            adjusted_timestamps = [
                {
                    "start_time": start + chunk_offsets[i],
                    "end_time": end + chunk_offsets[i],
                    "text": text
                }
                for start, end, text in timestamps
            ]
            all_timestamps.extend(adjusted_timestamps)

        full_transcription = " ".join(filter(None, transcriptions))
        return full_transcription, all_timestamps

    except Exception as e:
        print(f"Error processing audio: {str(e)}")
        return "", []


def find_best_window_match(jina_chunk, full_transcription, window_size=50, step=10):
    try:
        best_match = None
        highest_overlap = 0
        jina_words = set(jina_chunk.split())

        for i in range(0, len(full_transcription) - window_size, step):
            window = full_transcription[i:i+window_size]
            window_words = set(window.split())
            overlap = len(jina_words & window_words)

            if overlap > highest_overlap:
                highest_overlap = overlap
                best_match = i

        return best_match, highest_overlap
    except Exception as e:
        print(f"Error finding best window match: {str(e)}")
        return None, 0
    # Assuming we have the full transcription and its timestamps


def link_chunks_with_time(jina_chunks, transcription_chunks):
    """Link Jina chunks with their corresponding timestamps in the full transcription."""
    full_transcription = " ".join([chunk['text']
                                  for chunk in transcription_chunks])
    timestamps = [(chunk['start_time'], chunk['end_time'])
                  for chunk in transcription_chunks]

    linked_chunks = []
    # Start with the first timestamp's start time
    last_matched_end = timestamps[0][0]

    for i, jina_chunk in enumerate(jina_chunks):
        best_window_start, overlap = find_best_window_match(
            jina_chunk, full_transcription)

        if best_window_start is not None and overlap > 0:
            # Find the correct timestamp index
            timestamp_index = min(best_window_start //
                                  len(full_transcription), len(timestamps) - 1)
            start_time, end_time = timestamps[timestamp_index]

            linked_chunks.append({
                'jina_id': i,
                'jina_text': jina_chunk,
                'start_time': float(start_time),
                'end_time': float(end_time),
            })
            last_matched_end = end_time
        else:
            # For unmatched chunks, use the last matched end time as start time
            # and estimate an end time (e.g., 1 second later)
            linked_chunks.append({
                'jina_id': i,
                'jina_text': jina_chunk,
                'start_time': float(last_matched_end),
                # Assuming 1 second duration for unmatched chunks
                'end_time': float(last_matched_end + 1.0),
            })
            last_matched_end += 1.0

    # Sort the linked chunks by start time
    linked_chunks.sort(key=lambda x: x['start_time'])

    return linked_chunks
