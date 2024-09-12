import concurrent.futures
import io
import math
import os
import tempfile
import uuid

import speech_recognition as sr
import whisper
from fastapi import APIRouter, HTTPException
from pydub import AudioSegment
from pydub.silence import split_on_silence
from whisper.tokenizer import TO_LANGUAGE_CODE

r = sr.Recognizer()

model = whisper.load_model("tiny")

def extract_audio_from_video(video_bytes):
    """Extract audio from video bytes and return audio content."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
        temp_video.write(video_bytes)
        temp_video_path = temp_video.name

    try:
        video = AudioSegment.from_file(temp_video_path, format="mp4")
        audio_content = io.BytesIO()
        video.export(audio_content, format="wav")
        audio_content.seek(0)
        return audio_content.read()
    finally:
        os.unlink(temp_video_path)


def transcribe_audio_chunk(chunk, chunk_index, lang = "en"):
    """Transcribe a single audio chunk using Whisper."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_chunk:
        chunk = chunk.set_frame_rate(16000).set_channels(
            1)  # Ensure correct format
        chunk.export(temp_chunk.name, format="wav")
        temp_chunk_path = temp_chunk.name

    try:
        result = model.transcribe(temp_chunk_path, language=lang)
        # print(f"Chunk {chunk_index + 1} transcribed: {result['text']}")
        return result["text"]
    except Exception as e:
        print(f"Error during chunk {chunk_index + 1} transcription: {str(e)}")
        return ""
    finally:
        os.unlink(temp_chunk_path)


def process_audio_for_transcription(audio_content, max_workers=4, language="english"):
    """Process audio for transcription, dynamically splitting into chunks."""
    try:
        sound = AudioSegment.from_wav(io.BytesIO(audio_content))
        total_duration_ms = len(sound)

        # Dynamically calculate chunk size based on audio length
        # Aim for about 10 chunks, but no less than 30 seconds and no more than 5 minutes per chunk
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
            for future in concurrent.futures.as_completed(future_to_chunk):
                chunk_index = future_to_chunk[future]
                try:
                    text = future.result()
                    transcriptions[chunk_index] = text.strip()
                except Exception as e:
                    print(
                        f"Chunk {chunk_index + 1} generated an exception: {str(e)}")

        full_transcription = " ".join(filter(None, transcriptions))
        # print(f"Full transcription: {full_transcription}")
        return full_transcription
    except Exception as e:
        print(f"Error processing audio: {str(e)}")
        return ""
