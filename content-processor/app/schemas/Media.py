from pydantic import BaseModel

from app.schemas.Metadata import ImageSpecificMd, MediaSpecificMd, Metadata


class VideoRequest(BaseModel):
    video_id: str
    metadata: Metadata[MediaSpecificMd]

class AudioRequest(BaseModel):
    audio_id: str
    metadata: Metadata[MediaSpecificMd]

class ImageRequest(BaseModel):
    image_id: str
    metadata: Metadata[ImageSpecificMd]

class FileRequest(BaseModel):
    file_id: str
    metadata: Metadata[MediaSpecificMd]

