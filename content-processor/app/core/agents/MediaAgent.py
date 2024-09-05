import io
from abc import ABC, abstractmethod

import pytesseract
from PIL import Image
from PyPDF2 import PdfReader

from app.utils.AV import (extract_audio_from_video,
                          process_audio_for_transcription)
from app.utils.s3 import S3Operations

s3Opr = S3Operations()

class MediaAgent(ABC):
    def __init__(self, s3_media_key) -> None:
        super().__init__()
        self.s3_media_key = s3_media_key

    
    @abstractmethod
    async def process_media(self) -> dict:
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
    
class ImageAgent(MediaAgent):
    def process_media(self):
        image_bytes = s3Opr.download_object(object_key=self.s3_media_key)
        image = Image.open(io.BytesIO(image_bytes))
        transcript = pytesseract.image_to_string(image)

        return {"transcription": transcript}

class File_PDFAgent(MediaAgent):
    def process_media(self):
        pdf_bytes = s3Opr.download_object(object_key=self.s3_media_key)
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PdfReader(pdf_file)
        page_no = 1
        # Extract text from all pages
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
            text += "\n\n" + "*" * 50 + f"Page {page_no} ends" + "*" * 50 + "\n\n"
            page_no += 1
        return {"transcription": text}