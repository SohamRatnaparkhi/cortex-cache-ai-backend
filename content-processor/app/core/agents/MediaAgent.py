import io
import uuid
from abc import ABC, abstractmethod
from typing import Generic, List, TypeVar

import pytesseract
from PIL import Image
from pinecone.control.pinecone import Pinecone
from prisma.models import Memory
from PyPDF2 import PdfReader

from app.core.jina_ai import use_jina
from app.core.PineconeClient import PineconeClient
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import ImageSpecificMd, MediaSpecificMd, Metadata
from app.services.MemoryService import (insert_many_memories_to_db,
                                        insert_memory_to_db)
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
    
    async def embed_and_store_chunks(self, chunks: List[str], metadata: List[Metadata]):
        try:
            embeddings = use_jina.get_embedding(chunks)
            embeddings = [e["embedding"] for e in embeddings["data"]]

            print(f"Embedding dimension: {len(embeddings[0])}")
            
            vectors = get_vectors(metadata, embeddings)

            batch_size = 100
            pinecone_client = PineconeClient()
            pinecone_client.upsert_batch(vectors, batch_size)

            return 
        except Exception as e:
            raise RuntimeError(f"Error embedding and storing chunks: {str(e)}")
    


class VideoAgent(MediaAgent):
    async def process_media(self) -> AgentResponse:
        try:
            video_bytes = s3Opr.download_object(object_key=self.s3_media_key)
            audio_content = extract_audio_from_video(video_bytes)
            transcription = process_audio_for_transcription(audio_content=audio_content, language=self.md.language)
            
            mem_id = str(uuid.uuid4())
            self.md.mem_id = mem_id
            
            chunks = use_jina.segment_data(transcription)
            metadata = []
            chunk_id = 0
            for _ in chunks['chunks']:
                md_copy = self.md.model_copy()
                md_v = MediaSpecificMd(
                    chunk_id=f"{mem_id}_{chunk_id}",
                    type='video',
                )
                md_copy.specific_desc = md_v
                metadata.append(md_copy)
                chunk_id += 1

            if chunks['chunks']:
                chunks = chunks['chunks']
            else:
                chunks = [transcription]

            await self.store_memory_in_database(chunks, metadata, mem_id)
            await self.embed_and_store_chunks(chunks, metadata)

            response = AgentResponse(
                transcript=transcription,
                chunks=chunks,
                metadata=metadata
            )
            return response
        except Exception as e:
            print(f"Detailed error: {str(e)}")
            raise RuntimeError(f"Error processing video: {str(e)}")

    async def store_memory_in_database(self, chunks: List[str], metadata: List[Metadata], mem_id: str) -> None:
        try:
            memories = []
            i = 0
            for chunk, meta in zip(chunks, metadata):
                mem_data = {
                    "memId": mem_id,
                    "chunkId": f'{mem_id}_{i}',
                    "title": self.md.title,
                    "memData": chunk,
                    "memType": 'video',
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
            raise RuntimeError(f"Error storing video memory in database: {str(e)}")


class AudioAgent(MediaAgent):
    async def process_media(self) -> AgentResponse:
        try:
            audio_bytes = s3Opr.download_object(object_key=self.s3_media_key)
            transcription = process_audio_for_transcription(
                audio_content=audio_bytes, language=self.md.language)
            
            mem_id = str(uuid.uuid4())
            self.md.mem_id = mem_id
            
            chunks = use_jina.segment_data(transcription)
            metadata = []
            chunk_id = 0
            for _ in chunks['chunks']:
                md_copy = self.md.model_copy()
                md_v = MediaSpecificMd(
                    chunk_id=f"{mem_id}_{chunk_id}",
                    type='audio',
                )   
                md_copy.specific_desc = md_v
                metadata.append(md_copy)
                chunk_id += 1

            if chunks['chunks']:
                chunks = chunks['chunks']
            else:
                chunks = [transcription]

            await self.store_memory_in_database(chunks, metadata, mem_id)
            await self.embed_and_store_chunks(chunks, metadata)

            response = AgentResponse(
                transcript=transcription,
                chunks=chunks,
                metadata=metadata
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Error processing audio: {str(e)}")

    async def store_memory_in_database(self, chunks: List[str], metadata: List[Metadata], mem_id: str) -> None:
        try:
            memories = []
            i = 0
            for chunk, meta in zip(chunks, metadata):
                mem_data = {
                    "memId": mem_id,
                    "chunkId": f'{mem_id}_{i}',
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
            raise RuntimeError(f"Error storing audio memory in database: {str(e)}")


class ImageAgent(MediaAgent):
    async def process_media(self) -> AgentResponse:
        try:
            image_bytes = s3Opr.download_object(object_key=self.s3_media_key)
            image = Image.open(io.BytesIO(image_bytes))
            transcript = pytesseract.image_to_string(image)
            
            mem_id = str(uuid.uuid4())
            self.md.mem_id = mem_id
            
            chunks = use_jina.segment_data(transcript)
            metadata = []
            chunk_id = 0
            for _ in chunks['chunks']:
                md_copy = self.md.model_copy()
                md_v = MediaSpecificMd(
                    chunk_id=f"{mem_id}_{chunk_id}",
                    type='image',
                )
                md_copy.specific_desc = md_v
                metadata.append(md_copy)
                chunk_id += 1

            if chunks['chunks']:
                chunks = chunks['chunks']
            else:
                chunks = [transcript]

            await self.store_memory_in_database(chunks, metadata, mem_id)
            await self.embed_and_store_chunks(chunks, metadata)

            response = AgentResponse(
                transcript=transcript,
                chunks=chunks,
                metadata=metadata
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Error processing image: {str(e)}")

    async def store_memory_in_database(self, chunks: List[str], metadata: List[Metadata], mem_id: str) -> None:
        try:
            memories = []
            i = 0
            for chunk, meta in zip(chunks, metadata):
                mem_data = {
                    "memId": mem_id,
                    "chunkId": f"{mem_id}_{i}",
                    "title": self.md.title,
                    "memData": chunk,
                    "memType": 'image',
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
        
            mem_id = str(uuid.uuid4())
            self.md.mem_id = mem_id

            metadata = []
            for chunk_id, _ in enumerate(chunks):
                md_copy = self.md.model_copy()
                md_v = MediaSpecificMd(
                    chunk_id=f"{mem_id}_{chunk_id}",
                    type='pdf',
                )
                md_copy.specific_desc = md_v
                metadata.append(md_copy)

            await self.store_memory_in_database(chunks, metadata, mem_id)
            await self.embed_and_store_chunks(chunks, metadata)

            response = AgentResponse(
                transcript=full_text,
                chunks=chunks,
                metadata=metadata
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Error processing PDF: {str(e)}")

    async def store_memory_in_database(self, chunks: List[str], metadata: List[Metadata], mem_id: str) -> None:
        try:
            memories = []
            i = 0
            for chunk, meta in zip(chunks, metadata):
                mem_data = {
                    "memId": mem_id,
                    "chunkId": f"{mem_id}_{i}",
                    "title": self.md.title,
                    "memData": chunk,
                    "memType": 'pdf',
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
            raise RuntimeError(f"Error storing PDF memory in database: {str(e)}")
