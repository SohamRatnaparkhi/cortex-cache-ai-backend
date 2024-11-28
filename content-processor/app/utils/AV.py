import concurrent.futures
import io
import math
import os
import tempfile
import uuid

import numpy as np
import speech_recognition as sr
import whisper
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydub import AudioSegment
from pydub.silence import split_on_silence
from whisper.tokenizer import TO_LANGUAGE_CODE

r = sr.Recognizer()

model = whisper.load_model("tiny")

if os.path.exists('.env'):
    load_dotenv()

TEMP_FOLDER_PATH = os.getenv("TEMP_FOLDER_PATH", "/tmp")


TEMP_FOLDER_PATH = os.getenv("TEMP_FOLDER_PATH", "/tmp")


def extract_audio_from_video(video_bytes):
    """Extract audio from video bytes and return audio content."""
    temp_video_path = os.path.join(
        TEMP_FOLDER_PATH, f"temp_video_{os.urandom(4).hex()}.mp4")

    try:
        with open(temp_video_path, "wb") as temp_video:
            temp_video.write(video_bytes)

        video = AudioSegment.from_file(temp_video_path, format="mp4")
        audio_content = io.BytesIO()
        video.export(audio_content, format="wav")
        audio_content.seek(0)
        return audio_content.read()
    finally:
        if os.path.exists(temp_video_path):
            os.unlink(temp_video_path)


def safe_float_conversion(value):
    """Converts a value to a regular float if it's a numpy float."""
    if isinstance(value, np.floating):
        return float(value)
    return value


def transcribe_audio_chunk(chunk, chunk_index, lang="en"):
    """Transcribe a single audio chunk using Whisper."""
    temp_chunk_path = os.path.join(
        TEMP_FOLDER_PATH, f"temp_chunk_{chunk_index}_{os.urandom(4).hex()}.wav")

    try:
        # Ensure correct format and export
        chunk = chunk.set_frame_rate(16000).set_channels(1)
        chunk.export(temp_chunk_path, format="wav")

        result = model.transcribe(
            temp_chunk_path, language=lang, word_timestamps=True)

        timestamps = []
        for segment in result['segments']:
            start = safe_float_conversion(segment['start'])
            end = safe_float_conversion(segment['end'])
            text = segment['text']
            timestamps.append((start, end, text))

        text = " ".join([segment["text"] for segment in result["segments"]])
        return text, timestamps
    except Exception as e:
        print(f"Error during chunk {chunk_index + 1} transcription: {str(e)}")
        return "", []
    finally:
        if os.path.exists(temp_chunk_path):
            os.unlink(temp_chunk_path)


def process_audio_for_transcription(audio_content, max_workers=4, language="english"):
    """Process audio for transcription, dynamically splitting into chunks."""
    try:
        sound = AudioSegment.from_wav(io.BytesIO(audio_content))
        total_duration_ms = len(sound)

        # Dynamically calculate chunk size
        chunk_length_ms = max(min(total_duration_ms // 10, 300000), 30000)
        num_chunks = math.ceil(total_duration_ms / chunk_length_ms)

        # Split into initial chunks
        initial_chunks = [sound[i:i + chunk_length_ms]
                          for i in range(0, total_duration_ms, chunk_length_ms)]

        # Merge small chunks with the previous one
        merged_chunks = []
        current_chunk = initial_chunks[0]
        for next_chunk in initial_chunks[1:]:
            if len(next_chunk) < 300000:  # If the next chunk is less than 10 seconds
                current_chunk += next_chunk
            else:
                merged_chunks.append(current_chunk)
                current_chunk = next_chunk
        merged_chunks.append(current_chunk)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            language_code = TO_LANGUAGE_CODE.get(language, "en")
            future_to_chunk = {executor.submit(transcribe_audio_chunk, chunk, i, language_code): i
                               for i, chunk in enumerate(merged_chunks)}

            transcriptions = [""] * len(merged_chunks)
            all_timestamps = []
            chunk_offsets = [0]

            for future in concurrent.futures.as_completed(future_to_chunk):
                chunk_index = future_to_chunk[future]
                try:
                    text, timestamps = future.result()
                    transcriptions[chunk_index] = text.strip()

                    adjusted_timestamps = [{"start_time": start + chunk_offsets[chunk_index],
                                            "end_time": end + chunk_offsets[chunk_index],
                                            "text": text}
                                           for start, end, text in timestamps]
                    all_timestamps.extend(adjusted_timestamps)

                    if chunk_index < len(merged_chunks) - 1:
                        chunk_offsets.append(
                            chunk_offsets[chunk_index] + len(merged_chunks[chunk_index]) / 1000)
                except Exception as e:
                    print(
                        f"Chunk {chunk_index + 1} generated an exception: {str(e)}")

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
