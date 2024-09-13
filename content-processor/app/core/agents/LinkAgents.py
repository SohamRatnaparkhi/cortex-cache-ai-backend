import os
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, TypeVar

import requests
from dotenv import load_dotenv
from git import Union

from app.core.jina_ai import use_jina
from app.core.PineconeClient import PineconeClient
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import GitSpecificMd, Metadata, YouTubeSpecificMd
from app.services.MemoryService import (insert_many_memories_to_db,
                                        insert_memory_to_db)
from app.utils.Link import (extract_code_from_repo,
                            extract_transcript_from_youtube)
from app.utils.Vectors import get_vectors

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

            mem_id = str(uuid.uuid4())
            self.md.mem_id = mem_id

            # Add memory id to chunks' metadata
            for meta in meta_chunks:
                meta.mem_id = mem_id

            await self.store_memory_in_database(chunks, meta_chunks, mem_id)
            await self.embed_and_store_chunks(chunks, meta_chunks)

            return AgentResponse(
                chunks=chunks,
                metadata=meta_chunks,
                transcript=content,
            )
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise RuntimeError(f"Error processing Git repository: {str(e)}")

    async def store_memory_in_database(self, chunks: List[str], meta_chunks: List[GitSpecificMd], mem_id: str) -> None:
        try:
            memories = []
            for i, (chunk, meta) in enumerate(zip(chunks, meta_chunks)):
                mem_data = {
                    "memId": mem_id,
                    "chunkId": f"{mem_id}_{i}",
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
            raise RuntimeError(f"Error storing Git memory in database: {str(e)}")


class YoutubeAgent(LinkAgent[YouTubeSpecificMd]):
    """
    Agent for processing YouTube videos.
    """

    async def process_media(self) -> AgentResponse:
        """
        Process a YouTube video, extract its transcript, and segment it into chunks.

        This method performs the following steps:
        1. Extracts the video ID from the URL.
        2. Retrieves the video transcript and metadata.
        3. Segments the transcript into chunks using Jina AI.
        4. Fetches additional video metadata (author and channel name).
        5. Creates metadata for each chunk.

        Returns:
            AgentResponse: An object containing the segmented chunks, metadata, and full transcript.

        Raises:
            ValueError: If the transcript extraction fails.
            Exception: If there's any error during the processing of the YouTube video.
        """
        try:
            api_url = os.getenv("YOUTUBE_NO_EMBED_API_URL")
            video_url = self.resource_link
            video_id = video_url.split("/")[-1]
            if '?' in video_id:
                video_id = video_id.split('?')[0]
            transcript, video_title, video_desc = extract_transcript_from_youtube(video_url, language=self.md.language)
            
            mem_id = str(uuid.uuid4())

            self.md.mem_id = mem_id
            self.md.title = video_title
            self.md.description = video_desc
            if not transcript:
                raise ValueError("Failed to extract transcript from YouTube video")
            chunks = use_jina.segment_data(transcript)
            if chunks is not None and "chunks" in chunks.keys():
                chunks = chunks["chunks"]
            author = None
            channel_name = None
            response = requests.get(f"{api_url}{video_url}")
            if response.status_code == 200:
                data = response.json()
                author = data.get("author_name")
                channel_name = data.get("author_url").split('/')[-1]
            
            author = author or "Unknown"
            channel_name = channel_name or "Unknown"

            meta_chunks = []
            for i in range(len(chunks)):
                ymd = YouTubeSpecificMd(
                    video_id=video_id,
                    chunk_id=f'{mem_id}_{i}',
                    channel_name=channel_name,
                    author_name=author,
                )
                md_copy = self.md.model_copy()
                md_copy.specific_desc = ymd
                meta_chunks.append(md_copy)


            await self.store_memory_in_database(chunks, meta_chunks, mem_id)

            await self.embed_and_store_chunks(chunks, meta_chunks)

            return AgentResponse(
                transcript=transcript,
                chunks=chunks,
                metadata=meta_chunks,
            )
        except Exception as e:
            raise Exception(f"Error processing YouTube video: {str(e)}")

    async def store_memory_in_database(self, chunks: List[str], meta_chunks: List[YouTubeSpecificMd], mem_id: str) -> str:
        try:
            # combine chunk on left and right with current chunk for each chunk
            combined_chunks = []
            for i in range(len(chunks)):
                if i == 0:
                    combined_chunks.append({
                        "memData": chunks[i] + chunks[i+1],
                        "chunkId": f"{mem_id}_{i}",
                        "metadata": meta_chunks[i].json(),
                    })
                elif i == len(chunks) - 1:
                    combined_chunks.append({
                        "memData": chunks[i-1] + chunks[i],
                        "chunkId": f"{mem_id}_{i}",
                        "metadata": meta_chunks[i].json(),
                    })
                else:
                    combined_chunks.append({
                        "memData": chunks[i-1] + chunks[i],
                        "chunkId": f"{mem_id}_{i}",
                        "metadata": meta_chunks[i].json(),
                    })

            # make memory from chunks
            memories = []
            for chunk in combined_chunks:
                mem_data = {
                    "memId": mem_id,
                    "chunkId": chunk["chunkId"],
                    "title": self.md.title,
                    "memData": chunk["memData"],
                    "memType": 'youtube',
                    "source": self.md.source,
                    "tags": self.md.tags,
                    "metadata": chunk["metadata"],
                }
                memories.append(mem_data)
            # store memory in database using batches of n
            batch_size = 100
            for i in range(0, len(memories), batch_size):
                if batch_size + i > len(memories):
                    await insert_many_memories_to_db(memories[i: i + batch_size])
                else:
                    await insert_many_memories_to_db(memories[i: len(memories)])

        except Exception as e:
            raise RuntimeError(f"Error storing YouTube memory in database: {str(e)}")
