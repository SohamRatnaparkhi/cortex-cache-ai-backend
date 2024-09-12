import io
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

import pytesseract
from PIL import Image
from pinecone.control.pinecone import Pinecone
from prisma.models import Memory
from PyPDF2 import PdfReader

from app.core.jina_ai import use_jina
from app.core.PineconeClient import PineconeClient
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import ImageSpecificMd, MediaSpecificMd, Metadata
from app.services.MemoryService import insert_memory_to_db
from app.utils.AV import (extract_audio_from_video,
                          process_audio_for_transcription)
from app.utils.s3 import S3Operations
from app.utils.Vectors import flatten_metadata, get_vectors

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


class VideoAgent(MediaAgent):
    async def process_media(self) -> AgentResponse:
        try:
            video_bytes = s3Opr.download_object(object_key=self.s3_media_key)
            audio_content = extract_audio_from_video(video_bytes)
            transcription = process_audio_for_transcription(audio_content=audio_content, language=self.md.language)
            memory = await self.store_memory_in_database(transcription)
            memory_id = memory['id']
            self.md.mem_id = memory_id
            chunks = use_jina.segment_data(transcription)
            metadata = []
            chunk_id = 0
            for _ in chunks['chunks']:
                md_copy = self.md.model_copy()
                md_v = MediaSpecificMd(
                    chunk_id=f"{chunk_id}",
                    type='video',
                )
                md_copy.specific_desc = md_v
                metadata.append(md_copy)
                chunk_id += 1

            if  chunks['chunks']:
                chunks = chunks['chunks']   
            else:
                chunks = [transcription]
                
            embeddings = use_jina.get_embedding(chunks)
            embeddings = [e["embedding"] for e in embeddings["data"]]

            print(f"Embedding dimension: {len(embeddings[0])}")
            
            vectors = get_vectors(metadata, embeddings)

            batch_size = 100
            pinecone_client = PineconeClient()
            pinecone_client.upsert_batch(vectors, batch_size)


            response = AgentResponse(
                transcript=transcription,
                chunks=chunks,
                metadata=metadata
            )
            return response
        except Exception as e:
            print(f"Detailed error: {str(e)}")
            raise RuntimeError(f"Error processing video: {str(e)}")

    async def store_memory_in_database(self, data) -> dict:
        try:
            memory_data = {
                "title": self.md.title,
                "memData": data,
                "chunkIds": [],
                "memType": 'video',
                "source": self.md.source,
                "tags": self.md.tags,
                "metadata": self.md.specific_desc.json(),
            }
            memory = await insert_memory_to_db(memory_data)
            return {
                "id": str(memory.id),
                "title": memory.title,
                "memData": memory.memData,
                "chunkIds": memory.chunkIds,
                "memType": memory.memType,
                "source": memory.source,
                "tags": memory.tags,
                "metadata": memory.metadata,
                "createdAt": memory.createdAt.isoformat() if memory.createdAt else None,
                "updatedAt": memory.updatedAt.isoformat() if memory.updatedAt else None
            }
        except Exception as e:
            raise RuntimeError(f"Error storing memory in database: {str(e)}")


class AudioAgent(MediaAgent):
    async def process_media(self) -> AgentResponse:
        try:
            audio_bytes = s3Opr.download_object(object_key=self.s3_media_key)
            transcription = process_audio_for_transcription(
                audio_content=audio_bytes, language=self.md.language)
            memory = await self.store_memory_in_database(transcription)
            memory_id = memory['id']
            self.md.mem_id = memory_id
            chunks = use_jina.segment_data(transcription)
            metadata = []
            chunk_id = 0
            for _ in chunks['chunks']:
                md_copy = self.md.model_copy()
                md_v = MediaSpecificMd(
                    chunk_id=f"{chunk_id}",
                    type='audio',
                )   
                md_copy.specific_desc = md_v
                metadata.append(md_copy)
                chunk_id += 1

            if chunks['chunks']:
                chunks = chunks['chunks']
            else:
                chunks = [transcription]
                
            embeddings = use_jina.get_embedding(chunks)
            embeddings = [e["embedding"] for e in embeddings["data"]]

            print(f"Embedding dimension: {len(embeddings[0])}")
            
            vectors = get_vectors(metadata, embeddings)

            batch_size = 100
            pinecone_client = PineconeClient()
            pinecone_client.upsert_batch(vectors, batch_size)

            response = AgentResponse(
                transcript=transcription,
                chunks=chunks,
                metadata=metadata
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Error processing audio: {str(e)}")

    async def store_memory_in_database(self, data) -> dict:
        try:
            memory_data = {
                "title": self.md.title,
                "memData": data,
                "chunkIds": [],
                "memType": 'audio',
                "source": self.md.source,
                "tags": self.md.tags,
                "metadata": self.md.specific_desc.json(),
            }
            memory = await insert_memory_to_db(memory_data)
            return {
                "id": str(memory.id),
                "title": memory.title,
                "memData": memory.memData,
                "chunkIds": memory.chunkIds,
                "memType": memory.memType,
                "source": memory.source,
                "tags": memory.tags,
                "metadata": memory.metadata,
                "createdAt": memory.createdAt.isoformat() if memory.createdAt else None,
                "updatedAt": memory.updatedAt.isoformat() if memory.updatedAt else None
            }
        except Exception as e:
            raise RuntimeError(f"Error storing audio memory in database: {str(e)}")


class ImageAgent(MediaAgent):
    async def process_media(self) -> AgentResponse:
        try:
            image_bytes = s3Opr.download_object(object_key=self.s3_media_key)
            image = Image.open(io.BytesIO(image_bytes))
            transcript = pytesseract.image_to_string(image)
            memory = await self.store_memory_in_database(transcript)
            memory_id = memory['id']
            self.md.mem_id = memory_id
            chunks = use_jina.segment_data(transcript)
            metadata = []
            chunk_id = 0
            for _ in chunks['chunks']:
                md_copy = self.md.model_copy()
                md_v = MediaSpecificMd(
                    chunk_id=f"{chunk_id}",
                    type='image',
                )
                md_copy.specific_desc = md_v
                metadata.append(md_copy)
                chunk_id += 1

            if chunks['chunks']:
                chunks = chunks['chunks']
            else:
                chunks = [transcript]
                
            embeddings = use_jina.get_embedding(chunks)
            embeddings = [e["embedding"] for e in embeddings["data"]]

            print(f"Embedding dimension: {len(embeddings[0])}")
            
            vectors = get_vectors(metadata, embeddings)

            batch_size = 100
            pinecone_client = PineconeClient()
            pinecone_client.upsert_batch(vectors, batch_size)

            response = AgentResponse(
                transcript=transcript,
                chunks=chunks,
                metadata=metadata
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Error processing image: {str(e)}")

    async def store_memory_in_database(self, data) -> dict:
        try:
            memory_data = {
                "title": self.md.title,
                "memData": data,
                "chunkIds": [],
                "memType": 'image',
                "source": self.md.source,
                "tags": self.md.tags,
                "metadata": self.md.specific_desc.json(),
            }
            memory = await insert_memory_to_db(memory_data)
            return {
                "id": str(memory.id),
                "title": memory.title,
                "memData": memory.memData,
                "chunkIds": memory.chunkIds,
                "memType": memory.memType,
                "source": memory.source,
                "tags": memory.tags,
                "metadata": memory.metadata,
                "createdAt": memory.createdAt.isoformat() if memory.createdAt else None,
                "updatedAt": memory.updatedAt.isoformat() if memory.updatedAt else None
            }
        except Exception as e:
            raise RuntimeError(f"Error storing image memory in database: {str(e)}")


class File_PDFAgent(MediaAgent):
    async def process_media(self) -> AgentResponse:
        try:
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
                    if chunk['chunks']:
                        chunks.extend(chunk['chunks'])
                    chunking_data.clear()

            if chunking_data:
                chunk = use_jina.segment_data(''.join(chunking_data))
                chunks.extend(chunk['chunks'])

            full_text = '\n\n'.join(f"{page_content}\n\n{'*' * 50}Page {i} ends{'*' * 50}"
                                    for i, page_content in enumerate(text, 1))
        
            memory = await self.store_memory_in_database(full_text)
            memory_id = memory['id']
            self.md.mem_id = memory_id

            metadata = []
            chunk_id = 0
            for _ in chunks:
                md_copy = self.md.model_copy()
                md_v = MediaSpecificMd(
                    chunk_id=f"{chunk_id}",
                    type='pdf',
                )
                md_copy.specific_desc = md_v
                metadata.append(md_copy)
                chunk_id += 1

            embeddings = use_jina.get_embedding(chunks)
            embeddings = [e["embedding"] for e in embeddings["data"]]

            print(f"Embedding dimension: {len(embeddings[0])}")
            
            vectors = get_vectors(metadata, embeddings)

            batch_size = 100
            pinecone_client = PineconeClient()
            pinecone_client.upsert_batch(vectors, batch_size)

            response = AgentResponse(
                transcript=full_text,
                chunks=chunks,
                metadata=metadata
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Error processing PDF: {str(e)}")

    async def store_memory_in_database(self, data) -> dict:
        try:
            memory_data = {
                "title": self.md.title,
                "memData": data,
                "chunkIds": [],
                "memType": 'pdf',
                "source": self.md.source,
                "tags": self.md.tags,
                "metadata": self.md.specific_desc.json(),
            }
            memory = await insert_memory_to_db(memory_data)
            return {
                "id": str(memory.id),
                "title": memory.title,
                "memData": memory.memData,
                "chunkIds": memory.chunkIds,
                "memType": memory.memType,
                "source": memory.source,
                "tags": memory.tags,
                "metadata": memory.metadata,
                "createdAt": memory.createdAt.isoformat() if memory.createdAt else None,
                "updatedAt": memory.updatedAt.isoformat() if memory.updatedAt else None
            }
        except Exception as e:
            raise RuntimeError(f"Error storing PDF memory in database: {str(e)}")
