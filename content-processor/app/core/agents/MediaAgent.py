from abc import ABC, abstractmethod

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
        object = s3Opr.download_object()
