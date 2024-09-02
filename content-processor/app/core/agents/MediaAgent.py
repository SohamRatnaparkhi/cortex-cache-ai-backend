from abc import ABC, abstractmethod

from app.schemas.videos import ProcessVideo
from app.utils.AV import (extract_audio_from_video,
                          process_audio_for_transcription)
from app.utils.s3 import S3Operations

s3Opr = S3Operations()

class MediaAgent(ABC):
    def __init__(self, s3_media_key) -> None:
        super().__init__()
        self.s3_media_key = s3_media_key

    
    @abstractmethod
    async def process_media(self) -> str:
        pass


class VideoAgent(MediaAgent):
    def process_media(self):
        video_bytes = s3Opr.download_object(object_key=self.s3_media_key)
        audio_content = extract_audio_from_video(video_bytes)
        transcription = process_audio_for_transcription(
            audio_content=audio_content)

        return {"transcription": transcription}

class AudioAgent(MediaAgent):
    def process_media(self):
        audio_bytes = s3Opr.download_object(object_key=self.s3_media_key)
        transcription = process_audio_for_transcription(
            audio_content=audio_bytes)

        return {"transcription": transcription}