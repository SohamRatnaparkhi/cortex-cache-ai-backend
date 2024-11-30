import logging
import os
import re
import time
import uuid
from abc import ABC, abstractmethod
from typing import Generic, List, TypeVar

from dotenv import load_dotenv

from app.core.jina_ai import use_jina
from app.core.PineconeClient import PineconeClient
from app.core.voyage import voyage_client
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import (GitSpecificMd, Metadata, TextSpecificMd,
                                  YouTubeSpecificMd)
from app.services.MemoryService import insert_many_memories_to_db
from app.services.youtube_transcription import TranscriptChunker
from app.utils.chunk_processing import update_chunks
from app.utils.Link import extract_code_from_repo
from app.utils.Vectors import get_vectors

if (os.path.exists('.env')):
    load_dotenv()

T = TypeVar('T', YouTubeSpecificMd, GitSpecificMd)


class LinkAgent(ABC, Generic[T]):
    """
    Abstract base class for link agents that process different types of media.

    Attributes:
        resource_link (str): The URL of the resource to process.
        md (Metadata[T]): Metadata associated with the resource.
    """

    def __init__(self, resource_link: str, md: Metadata[T]) -> None:
        super().__init__()
        self.resource_link = resource_link
        self.md = md

    @abstractmethod
    def process_media(self) -> AgentResponse:
        """
        Abstract method to process the media.

        Returns:
            AgentResponse: The processed media content.
        """
        pass

    async def embed_and_store_chunks(self, chunks: List[str], metadata: List[Metadata]):
        try:
            logger.debug("l1 = " + str(len(chunks)))
            title = self.md.title
            description = self.md.description
            preprocessed_chunks = await update_chunks(chunks=chunks)
            preprocessed_chunks = [
                title + " " + description + " " + chunk for chunk in preprocessed_chunks]

            # embeddings = use_jina.get_embedding(preprocessed_chunks)

            # embeddings = [e["embedding"]
            #               for e in embeddings if "embedding" in e.keys()]
            embeddings = voyage_client.get_embeddings(preprocessed_chunks)
            logger.debug("l2 = " + str(len(embeddings)))

            logger.debug(f"Embedding dimensions: {len(embeddings[0])}")

            vectors = get_vectors(metadata, embeddings)

            logger.debug(len(metadata))
            logger.debug(len(vectors))

            batch_size = 100
            pinecone_client = PineconeClient()
            res = pinecone_client.upsert(vectors, batch_size)
            logger.debug(res)
            return
        except Exception as e:
            raise RuntimeError(f"Error embedding and storing chunks: {str(e)}")


class GitAgent(LinkAgent[GitSpecificMd]):
    """
    Agent for processing Git repositories.
    """

    async def process_media(self) -> AgentResponse:
        """
        Process a Git repository, extract its code, and segment it into chunks with metadata.

        This method performs the following steps:
        1. Extracts code from the repository.
        2. Segments the code into chunks.
        3. Creates metadata for each chunk.
        4. Stores the chunks as memories in the database.
        5. Embeds and stores the chunks in the vector database.

        Returns:
            AgentResponse: An object containing the segmented chunks, metadata, and full content.

        Raises:
            ValueError: If code extraction from the repository fails.
            RuntimeError: If there's an error processing the Git repository.
        """
        try:
            repo_url = self.resource_link
            code = extract_code_from_repo(repo_url=repo_url, metadata=self.md)

            chunks = code.chunks
            meta_chunks = code.metadata
            content = code.transcript

            memId = str(uuid.uuid4())
            self.md.memId = memId

            # Add memory id to chunks' metadata
            for meta in meta_chunks:
                meta.memId = memId

            print("Total chunks: ", len(chunks))

            await self.embed_and_store_chunks(chunks, meta_chunks)
            await self.store_memory_in_database(chunks, meta_chunks, memId)

            return AgentResponse(
                chunks=chunks,
                metadata=meta_chunks,
                transcript=content,
                userId=self.md.user_id,
                memoryId=memId,
            )
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise RuntimeError(f"Error processing Git repository: {str(e)}")

    async def store_memory_in_database(self, chunks: List[str], meta_chunks: List[GitSpecificMd], memId: str) -> None:
        try:
            memories = []
            for i, (chunk, meta) in enumerate(zip(chunks, meta_chunks)):
                mem_data = {
                    "memId": memId,
                    "userId": self.md.user_id,
                    "chunkId": f"{memId}_{i}",
                    "title": self.md.title,
                    "memData": chunk,
                    "memType": 'git',
                    "source": self.md.source,
                    "tags": self.md.tags,
                    "metadata": meta.json(),
                }
                memories.append(mem_data)

            # Store memory in database using batches
            batch_size = 100
            for i in range(0, len(memories), batch_size):
                batch = memories[i:i + batch_size]
                await insert_many_memories_to_db(batch)

        except Exception as e:
            raise RuntimeError(
                f"Error storing Git memory in database: {str(e)}")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format"""
    if seconds is None:
        return None

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class YoutubeAgent(LinkAgent[YouTubeSpecificMd]):
    """
    Agent for processing YouTube videos.
    """

    async def process_media(self) -> AgentResponse:
        """
        Process a YouTube video, extract its transcript, and segment it into chunks.
        """
        try:
            self.chunker = TranscriptChunker(
                max_tokens=800,
                min_tokens=100,
                overlap_tokens=100
            )
            start_time = time.time()
            api_url = os.getenv("YOUTUBE_NO_EMBED_API_URL")
            video_url = self.resource_link
            video_id = self.chunker.extract_video_id(video_url)

            # Process video and get chunks with metadata
            extract_start = time.time()
            chunks, video_title, video_desc, author, channel_name = await self.chunker.process_video(
                video_url, api_url
            )
            extract_end = time.time()
            logger.info(
                f"Transcript extraction took {extract_end - extract_start:.2f} seconds")

            # Update metadata
            memId = str(uuid.uuid4())
            self.md.source = video_url
            self.md.memId = memId
            self.md.title = video_title + " - " + self.md.title if self.md.title else ""
            self.md.description = video_desc

            # Create metadata for each chunk
            metadata_start = time.time()
            meta_chunks = []
            formatted_chunks = []

            for i, chunk in enumerate(chunks):
                # Create YouTube specific metadata
                ymd = YouTubeSpecificMd(
                    video_id=video_id,
                    chunk_id=f'{memId}_{i}',
                    channel_name=channel_name,
                    author_name=author,
                    start_time=format_timestamp(chunk['start_time']),
                    end_time=format_timestamp(chunk['end_time']),
                )

                # Copy base metadata and add specific metadata
                md_copy = self.md.model_copy()
                md_copy.specific_desc = ymd
                meta_chunks.append(md_copy)

                # Format chunk for storage
                formatted_chunks.append(chunk['text'])

            metadata_end = time.time()
            logger.info(
                f"Metadata creation took {metadata_end - metadata_start:.2f} seconds")

            # Store in database
            store_start = time.time()
            await self.store_memory_in_database(formatted_chunks, meta_chunks, memId)
            store_end = time.time()
            logger.info(
                f"Storing memory took {store_end - store_start:.2f} seconds")

            # Embed and store chunks
            embed_start = time.time()
            await self.embed_and_store_chunks(formatted_chunks, meta_chunks)
            embed_end = time.time()
            logger.info(
                f"Embedding and storing took {embed_end - embed_start:.2f} seconds")

            end_time = time.time()
            logger.info(
                f"Total processing time: {end_time - start_time:.2f} seconds")

            # Combine all text for full transcript
            full_transcript = " ".join(formatted_chunks)

            return AgentResponse(
                transcript=full_transcript,
                chunks=formatted_chunks,
                metadata=meta_chunks,
                userId=self.md.user_id,
                memoryId=memId,
            )

        except Exception as e:
            raise Exception(f"Error processing YouTube video: {str(e)}")

    async def store_memory_in_database(self, chunks: List[str], meta_chunks: List[TextSpecificMd], memId: str):
        try:
            memories = []
            for i, (chunk, meta) in enumerate(zip(chunks, meta_chunks)):
                mem_data = {
                    "memId": memId,
                    "userId": self.md.user_id,
                    "chunkId": f"{memId}_{i}",
                    "title": self.md.title,
                    "memData": chunk,
                    "memType": 'youtube',
                    "source": self.md.source,
                    "tags": self.md.tags,
                    "metadata": meta.json(),
                }
                memories.append(mem_data)

            batch_size = 100
            for i in range(0, len(memories), batch_size):
                batch = memories[i:i + batch_size]
                await insert_many_memories_to_db(batch)

        except Exception as e:
            raise RuntimeError(
                f"Error storing Web memory in database: {str(e)}")


class WebAgent(LinkAgent[TextSpecificMd]):
    """
    Agent for processing web pages.
    """

    async def process_media(self) -> AgentResponse:
        """
        Process a web page, extract its text, and segment it into chunks.
        """
        link = self.resource_link

        response = use_jina.web_scraper(link)
        print(f"Web Scraper Response: {response}")
        if response is not None:
            content = response.get("data").get("content")
            title = response.get("data").get("title")
            description = response.get("data").get("description")

            #  filter all tags from content
            content = re.sub(r'<[^>]+>', '', content)
            chunks = use_jina.segment_data(content)
            # if chunks is not None and "chunks" in chunks.keys():
            #     chunks = chunks["chunks"]

            memId = str(uuid.uuid4())
            self.md.memId = memId
            self.md.title += " " + title
            self.md.description += " " + description

            meta_chunks = []
            for i in range(len(chunks)):
                tmd = TextSpecificMd(
                    chunk_id=f'{memId}_{i}',
                    url=link,
                )
                md_copy = self.md.model_copy()
                md_copy.specific_desc = tmd
                meta_chunks.append(md_copy)

            await self.embed_and_store_chunks(chunks, meta_chunks)
            await self.store_memory_in_database(chunks, meta_chunks, memId)

            return AgentResponse(
                chunks=chunks,
                metadata=meta_chunks,
                transcript=content,
                userId=self.md.user_id,
                memoryId=memId,
            )

    async def store_memory_in_database(self, chunks: List[str], meta_chunks: List[TextSpecificMd], memId: str):
        try:
            memories = []
            for i, (chunk, meta) in enumerate(zip(chunks, meta_chunks)):
                mem_data = {
                    "memId": memId,
                    "userId": self.md.user_id,
                    "chunkId": f"{memId}_{i}",
                    "title": self.md.title,
                    "memData": chunk,
                    "memType": 'web',
                    "source": self.md.source,
                    "tags": self.md.tags,
                    "metadata": meta.json(),
                }
                memories.append(mem_data)

            batch_size = 100
            for i in range(0, len(memories), batch_size):
                batch = memories[i:i + batch_size]
                await insert_many_memories_to_db(batch)

        except Exception as e:
            raise RuntimeError(
                f"Error storing Web memory in database: {str(e)}")
