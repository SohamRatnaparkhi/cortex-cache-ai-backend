import os

from fastapi import APIRouter, HTTPException

from app.schemas.videos import ProcessVideo
from app.utils.AV import (extract_audio_from_video,
                          process_audio_for_transcription)
from app.utils.s3 import S3Operations

router = APIRouter(
    prefix='/api/v1/videos',
    tags=["videos"],
    responses={404: {"description": "Not found"}},
)


@router.post("/process")
async def process_video(request: ProcessVideo.ProcessVideoRequest) -> dict:
    """Process video, extract audio, and transcribe."""
    try:
        s3Opr = S3Operations()
        video_bytes = s3Opr.download_object(object_key=request.video_id)

        # save file in tmp dir by creating folder tmp/vid/(key)
        # create folder
        if not os.path.exists("tmp/vid"):
            os.makedirs("tmp/vid")


        with open(f"tmp/vid/{request.video_id}", "wb") as f:
            f.write(video_bytes)

        # Extract audio from video
        audio_content = extract_audio_from_video(video_bytes)

        # save audio content
        with open(f"tmp/vid/{request.video_id}.wav", "wb") as f:
            f.write(audio_content)

        # Transcribe audio
        transcription = process_audio_for_transcription(audio_content=audio_content, chunk_length_ms=8000)

        return {"transcription": transcription}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
