import io
import uuid
from abc import ABC, abstractmethod
from typing import Generic, List, TypeVar

import pytesseract
from PIL import Image
from PyPDF2 import PdfReader

from app.core.jina_ai import use_jina
from app.core.PineconeClient import PineconeClient
from app.core.voyage import voyage_client
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import ImageSpecificMd, MediaSpecificMd, Metadata
from app.services.MemoryService import insert_many_memories_to_db
from app.utils.app_logger_config import logger
from app.utils.AV import (extract_audio_from_video,
                          process_audio_for_transcription)
from app.utils.chunk_processing import update_chunks
# from app.utils.chunk_preprocessing import update_chunks
from app.utils.s3 import S3Operations
from app.utils.status_tracking import TRACKER, ProcessingStatus
from app.utils.Vectors import combine_data_chunks, get_vectors

s3Opr = S3Operations()

T = TypeVar('T', MediaSpecificMd, ImageSpecificMd)


class MediaAgent(ABC, Generic[T]):
    def __init__(self, s3_media_key, md: Metadata[T]) -> None:
        super().__init__()
        self.s3_media_key = s3_media_key
        self.md = md

    @abstractmethod
    async def process_media(self) -> AgentResponse:
        pass

    @abstractmethod
    async def store_memory_in_database(self, data) -> dict:
        pass

    async def embed_and_store_chunks(self, chunks: List[str], metadata: List[Metadata]):
        try:
            logger.debug(f"Embedding and storing chunks: {len(chunks)}")

            preprocessed_chunks = await update_chunks(chunks=chunks, userId=self.md.user_id, memoryId=self.md.memId)

            title = self.md.title
            description = self.md.description

            preprocessed_chunks = [
                title + " " + description + " " + chunk for chunk in preprocessed_chunks]

            embeddings = voyage_client.get_embeddings(preprocessed_chunks)
            logger.debug(f"Length after embedding: {len(embeddings)}")

            logger.debug(f"Embedding dimensions: {len(embeddings[0])}")

            vectors = get_vectors(metadata, embeddings)

            batch_size = 100
            pinecone_client = PineconeClient()
            # pinecone_client.upsert_batch(vectors, batch_size)
            TRACKER.update_status(
                user_id=self.md.user_id, document_id=self.md.memId, status=ProcessingStatus.STORING_VECTORS, progress=85)
            res = pinecone_client.upsert(vectors, batch_size)
            logger.debug(f"Upsert response: {res}")
            return preprocessed_chunks
        except Exception as e:
            raise RuntimeError(f"Error embedding and storing chunks: {str(e)}")


class VideoAgent(MediaAgent):
    async def process_media(self) -> AgentResponse:
        try:
            memId = str(uuid.uuid4())
            self.md.memId = memId

            TRACKER.create_status(
                user_id=self.md.user_id, document_id=memId, document_title=self.md.title
            )

            video_bytes = s3Opr.download_object(object_key=self.s3_media_key)
            audio_content = await extract_audio_from_video(video_bytes)

            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.PROCESSING, progress=15
            )
            transcription, timestamps = await process_audio_for_transcription(
                audio_content=audio_content, language=self.md.language)
            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.PROCESSING, progress=20
            )

            chunks = use_jina.segment_data(transcription)
            metadata = []
            chunk_id = 0
            for _ in chunks:
                md_copy = self.md.model_copy()
                md_v = MediaSpecificMd(
                    chunk_id=f"{memId}_{chunk_id}",
                    type='video',
                    end_time=timestamps[chunk_id]["end_time"] if chunk_id < len(
                        timestamps) else 0,
                    start_time=timestamps[chunk_id]["start_time"] if chunk_id < len(
                        timestamps) else 0
                )
                md_copy.specific_desc = md_v
                metadata.append(md_copy)
                chunk_id += 1

            if not chunks:
                chunks = [transcription]

            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.CREATING_EMBEDDINGS, progress=20
            )
            await self.embed_and_store_chunks(chunks, metadata)
            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.STORING_DOCUMENT, progress=90
            )
            await self.store_memory_in_database(chunks, metadata, memId)
            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.COMPLETED, progress=100
            )
            response = AgentResponse(
                transcript=transcription,
                chunks=chunks,
                metadata=metadata,
                userId=self.md.user_id,
                memoryId=memId
            )
            return response
        except Exception as e:
            print(f"Detailed error: {str(e)}")
            raise RuntimeError(f"Error processing video: {str(e)}")

    async def store_memory_in_database(self, chunks: List[str], metadata: List[Metadata], memId: str) -> None:
        try:
            memories = []
            combined_chunks = combine_data_chunks(chunks, metadata, memId)
            i = 0
            for chunk in combined_chunks:
                mem_data = {
                    "memId": memId,
                    "userId": self.md.user_id,
                    "chunkId": f'{memId}_{i}',
                    "title": self.md.title,
                    "userId": self.md.user_id,
                    "memType": 'video',
                    "memData": chunk["memData"],
                    "source": self.md.source,
                    "tags": self.md.tags,
                    "metadata": chunk["metadata"],
                }
                memories.append(mem_data)
                i += 1
            batch_size = 100

            for i in range(0, len(memories), batch_size):
                batch = memories[i:i + batch_size]
                await insert_many_memories_to_db(batch)

        except Exception as e:
            raise RuntimeError(
                f"Error storing video memory in database: {str(e)}")


class AudioAgent(MediaAgent):
    async def process_media(self) -> AgentResponse:
        try:
            memId = str(uuid.uuid4())
            self.md.memId = memId

            TRACKER.create_status(
                user_id=self.md.user_id, document_id=memId, document_title=self.md.title
            )

            audio_bytes = s3Opr.download_object(object_key=self.s3_media_key)

            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.PROCESSING, progress=15
            )

            transcription, _ = await process_audio_for_transcription(
                audio_content=audio_bytes, language=self.md.language)

            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.PROCESSING, progress=20
            )

            chunks = use_jina.segment_data(transcription)
            metadata = []
            chunk_id = 0
            for _ in chunks:
                md_copy = self.md.model_copy()
                md_v = MediaSpecificMd(
                    chunk_id=f"{memId}_{chunk_id}",
                    type='audio',
                )
                md_copy.specific_desc = md_v
                metadata.append(md_copy)
                chunk_id += 1

            if not chunks:
                chunks = [transcription]
            chunks = [transcription]

            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.CREATING_EMBEDDINGS, progress=20
            )
            await self.embed_and_store_chunks(chunks, metadata)

            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.STORING_DOCUMENT, progress=90
            )

            await self.store_memory_in_database(chunks, metadata, memId)

            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.COMPLETED, progress=100
            )

            response = AgentResponse(
                transcript=transcription,
                chunks=chunks,
                metadata=metadata,
                userId=self.md.user_id,
                memoryId=memId
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Error processing audio: {str(e)}")

    async def store_memory_in_database(self, chunks: List[str], metadata: List[Metadata], memId: str) -> None:
        try:
            memories = []
            i = 0
            for chunk, meta in zip(chunks, metadata):
                mem_data = {
                    "memId": memId,
                    "chunkId": f'{memId}_{i}',
                    "title": self.md.title,
                    "memData": chunk,
                    "memType": 'audio',
                    "source": self.md.source,
                    "tags": self.md.tags,
                    "metadata": meta.json(),
                }
                memories.append(mem_data)
                i += 1

            batch_size = 100
            for i in range(0, len(memories), batch_size):
                batch = memories[i:i + batch_size]
                await insert_many_memories_to_db(batch)
        except Exception as e:
            raise RuntimeError(
                f"Error storing audio memory in database: {str(e)}")


class ImageAgent(MediaAgent):
    async def process_media(self) -> AgentResponse:
        try:
            memId = str(uuid.uuid4())
            self.md.memId = memId

            TRACKER.create_status(
                user_id=self.md.user_id, document_id=memId, document_title=self.md.title
            )

            image_bytes = s3Opr.download_object(object_key=self.s3_media_key)

            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.PROCESSING, progress=15
            )
            image = Image.open(io.BytesIO(image_bytes))
            transcript = pytesseract.image_to_string(image)

            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.PROCESSING, progress=20
            )

            chunks = use_jina.segment_data(transcript)
            metadata = []
            chunk_id = 0
            for _ in chunks:
                md_copy = self.md.model_copy()
                md_v = ImageSpecificMd(
                    chunk_id=f"{memId}_{chunk_id}",
                    type='image',
                    width=image.width or 0,
                    height=image.height or 0,
                    format=image.format or ""
                )
                md_copy.specific_desc = md_v
                metadata.append(md_copy)
                chunk_id += 1
            if not chunks:
                chunks = [transcript]
            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.CREATING_EMBEDDINGS, progress=20
            )
            await self.embed_and_store_chunks(chunks, metadata)
            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.STORING_DOCUMENT, progress=90
            )
            await self.store_memory_in_database(chunks, metadata, memId)
            response = AgentResponse(
                transcript=transcript,
                chunks=chunks,
                metadata=metadata,
                userId=self.md.user_id,
                memoryId=memId
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Error processing image: {str(e)}")

    async def store_memory_in_database(self, chunks: List[str], metadata: List[Metadata], memId: str) -> None:
        try:
            memories = []
            combined_memories = combine_data_chunks(chunks, metadata, memId)
            i = 0
            for chunk in combined_memories:
                mem_data = {
                    "memId": memId,
                    "userId": self.md.user_id,
                    "chunkId": f"{memId}_{i}",
                    "title": self.md.title,
                    "memData": chunk["memData"],
                    "memType": 'image',
                    "source": self.md.source,
                    "tags": self.md.tags,
                    "metadata": chunk["metadata"],
                }
                memories.append(mem_data)
                i += 1
            batch_size = 100
            for i in range(0, len(memories), batch_size):
                batch = memories[i:i + batch_size]
                await insert_many_memories_to_db(batch)

        except Exception as e:
            raise RuntimeError(
                f"Error storing image memory in database: {str(e)}")


class File_PDFAgent(MediaAgent):
    async def process_media(self) -> AgentResponse:
        try:
            memId = str(uuid.uuid4())
            self.md.memId = memId
            TRACKER.create_status(
                user_id=self.md.user_id, document_id=memId, document_title=self.md.title
            )

            pdf_bytes = s3Opr.download_object(object_key=self.s3_media_key)

            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.PROCESSING, progress=5
            )

            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))

            combine_pages = min(5, len(pdf_reader.pages))
            chunks = []
            text = []
            chunking_data = []

            for page_no, page in enumerate(pdf_reader.pages, 1):
                page_text = sanitize_input(page.extract_text())
                # page_text = page.extract_text()
                text.append(page_text)
                chunking_data.append(page_text.replace('\n', ''))

                if page_no % combine_pages == 0:
                    chunk = use_jina.segment_data(''.join(chunking_data))
                    if chunk:
                        chunks.extend(chunk)
                    chunking_data.clear()

            if chunking_data:
                chunk = use_jina.segment_data(''.join(chunking_data))
                chunks.extend(chunk)

            full_text = '\n\n'.join(f"{page_content}\n\n{'*' * 50}Page {i} ends{'*' * 50}"
                                    for i, page_content in enumerate(text, 1))

            metadata = []
            for chunk_id, _ in enumerate(chunks):
                md_copy = self.md.model_copy()
                md_v = MediaSpecificMd(
                    chunk_id=f"{memId}_{chunk_id}",
                    type='pdf',
                )
                md_copy.specific_desc = md_v
                metadata.append(md_copy)

            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.CREATING_EMBEDDINGS, progress=15)

            preprocessed_chunks = await self.embed_and_store_chunks(chunks, metadata)

            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.STORING_DOCUMENT, progress=90)
            await self.store_memory_in_database(chunks, preprocessed_chunks, metadata, memId)

            TRACKER.update_status(
                user_id=self.md.user_id, document_id=memId, status=ProcessingStatus.COMPLETED, progress=100)

            response = AgentResponse(
                transcript=full_text,
                chunks=chunks,
                metadata=metadata,
                userId=self.md.user_id,
                memoryId=memId
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Error processing PDF: {str(e)}")

    async def store_memory_in_database(self, chunks: List[str], preprocessed_chunks: List[str], metadata: List[Metadata], memId: str) -> None:
        try:
            memories = []
            combined_chunks = combine_data_chunks(chunks, metadata, memId)
            i = 0
            for chunk in combined_chunks:
                mem_data = {
                    "memId": memId,
                    "userId": self.md.user_id,
                    "chunkId": f"{memId}_{i}",
                    "title": self.md.title,
                    "memData": chunk["memData"],
                    "memType": 'pdf',
                    "source": self.md.source,
                    "tags": self.md.tags,
                    "metadata": chunk["metadata"],
                }
                memories.append(mem_data)
                i += 1

            batch_size = 100
            for i in range(0, len(memories), batch_size):
                batch = memories[i:i + batch_size]
                await insert_many_memories_to_db(batch, preprocessed_chunks=preprocessed_chunks[i: i + batch_size])

        except Exception as e:
            raise RuntimeError(
                f"Error storing PDF memory in database: {str(e)}")


def sanitize_input(data: str) -> str:
    sanitized_data = data.replace('\x00', '')
    return sanitized_data
