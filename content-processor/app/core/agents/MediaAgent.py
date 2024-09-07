import io
from abc import ABC, abstractmethod

import pytesseract
from app.core.jina_ai import use_jina
from app.utils.AV import (extract_audio_from_video,
                          process_audio_for_transcription)
from app.utils.s3 import S3Operations
from PIL import Image
from PyPDF2 import PdfReader

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
        try:
            video_bytes = s3Opr.download_object(object_key=self.s3_media_key)
            audio_content = extract_audio_from_video(video_bytes)
            transcription = process_audio_for_transcription(audio_content=audio_content)
            chunks = use_jina.segment_data(transcription)
            if "chunks" in chunks.keys():
                return {"transcription": transcription, "chunks": chunks['chunks']}
            return {"chunks": chunks, "transcription": transcription}
        except Exception as e:
            raise RuntimeError(f"Error processing video: {str(e)}")


class AudioAgent(MediaAgent):
    def process_media(self):
        audio_bytes = s3Opr.download_object(object_key=self.s3_media_key)
        transcription = process_audio_for_transcription(
            audio_content=audio_bytes)
        chunks = use_jina.segment_data(transcription)
        return {"transcription": transcription, "chunks": chunks['chunks']}


class ImageAgent(MediaAgent):
    def process_media(self):
        image_bytes = s3Opr.download_object(object_key=self.s3_media_key)
        image = Image.open(io.BytesIO(image_bytes))
        transcript = pytesseract.image_to_string(image)
        chunks = use_jina.segment_data(transcript)
        return {"transcription": transcript, "chunks": chunks['chunks']}


class File_PDFAgent(MediaAgent):
    def process_media(self):
        pdf_bytes = s3Opr.download_object(object_key=self.s3_media_key)
        pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
        
        combine_pages = min(5, len(pdf_reader.pages))
        chunks = []
        text = []
        chunking_data = []

        for page_no, page in enumerate(pdf_reader.pages, 1):
            page_text = page.extract_text()
            text.append(page_text)
            chunking_data.append(page_text.replace('\n', ''))
            
            if page_no % combine_pages == 0:
                chunk = use_jina.segment_data(''.join(chunking_data))
                chunks.extend(chunk['chunks'])
                chunking_data.clear()

        if chunking_data:
            chunk = use_jina.segment_data(''.join(chunking_data))
            chunks.extend(chunk['chunks'])

        full_text = '\n\n'.join(f"{page_content}\n\n{'*' * 50}Page {i} ends{'*' * 50}"
                                for i, page_content in enumerate(text, 1))

        return {"transcription": full_text, "chunks": chunks}
