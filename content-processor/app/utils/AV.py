import io
import os
import tempfile
import uuid

import speech_recognition as sr
import whisper
from fastapi import APIRouter, HTTPException
from pydub import AudioSegment
from pydub.silence import split_on_silence

r = sr.Recognizer()

model = whisper.load_model("base")


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


def transcribe_audio_whisper(audio_content):
    """Transcribe audio using Whisper."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        temp_audio.write(audio_content)
        temp_audio_path = temp_audio.name

    try:
        # Transcribe audio
        result = model.transcribe(temp_audio_path)
        print(result)
        return result["text"]
    except Exception as e:
        print(f"Error during transcription: {str(e)}")
        return ""
    finally:
        os.unlink(temp_audio_path)


def process_audio_for_transcription(audio_content, use_chunks=True, chunk_length_ms=60000):
    """Process audio for transcription, with option to use chunks or not."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        temp_audio.write(audio_content)
        temp_audio_path = temp_audio.name

    try:
        if use_chunks:
            sound = AudioSegment.from_wav(temp_audio_path)
            chunks = [sound[i:i + chunk_length_ms]
                      for i in range(0, len(sound), chunk_length_ms)]

            whole_text = ""
            for i, audio_chunk in enumerate(chunks, start=1):
                chunk_content = io.BytesIO()
                audio_chunk.export(chunk_content, format="wav")
                chunk_content.seek(0)

                text = transcribe_audio_whisper(chunk_content.read())
                if text:
                    whole_text += f"{text.capitalize()}. "
                print(f"Chunk {i}: {text}")  # Debug print

            return whole_text
        else:
            # Process the entire audio file at once
            return transcribe_audio_whisper(audio_content)
    finally:
        os.unlink(temp_audio_path)
