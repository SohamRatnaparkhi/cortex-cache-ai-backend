import uuid
from typing import List

from app.core.jina_ai import use_jina
from app.core.PineconeClient import PineconeClient
from app.core.voyage import voyage_client
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import Metadata, NoteSpecificMd
from app.services.MemoryService import insert_many_memories_to_db
from app.utils.app_logger_config import logger
from app.utils.chunk_processing import update_chunks
from app.utils.status_tracking import TRACKER, ProcessingStatus
from app.utils.Vectors import combine_data_chunks, get_vectors


class TextAgent:
    def __init__(self, text: str, md: Metadata) -> None:
        self.text = text
        self.md = md

    async def process_media(self) -> AgentResponse:
        try:
            memId = str(uuid.uuid4())
            self.md.memId = memId

            TRACKER.create_status(
                user_id=self.md.user_id,
                document_id=memId,
                document_title=self.md.title
            )

            TRACKER.update_status(
                user_id=self.md.user_id,
                document_id=memId,
                status=ProcessingStatus.PROCESSING,
                progress=20
            )

            # Segment the text into chunks
            chunks = use_jina.segment_data(self.text)

            # Create metadata for each chunk
            metadata = []
            chunk_id = 0
            for _ in chunks:
                md_copy = self.md.model_copy()
                md_v = NoteSpecificMd(
                    chunk_id=f"{memId}_{chunk_id}",
                )
                md_copy.specific_desc = md_v
                metadata.append(md_copy)
                chunk_id += 1

            # If chunking resulted in no chunks, use the entire text as one chunk
            if not chunks:
                chunks = [self.text]

            TRACKER.update_status(
                user_id=self.md.user_id,
                document_id=memId,
                status=ProcessingStatus.CREATING_EMBEDDINGS,
                progress=40
            )

            # Embed and store chunks
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
                TRACKER.update_status(
                    user_id=self.md.user_id,
                    document_id=self.md.memId,
                    status=ProcessingStatus.STORING_VECTORS,
                    progress=85
                )
                res = pinecone_client.upsert(vectors, batch_size)
                logger.debug(f"Upsert response: {res}")
            except Exception as e:
                raise RuntimeError(
                    f"Error embedding and storing chunks: {str(e)}")

            TRACKER.update_status(
                user_id=self.md.user_id,
                document_id=memId,
                status=ProcessingStatus.STORING_DOCUMENT,
                progress=90
            )

            # Store in database
            await self.store_memory_in_database(chunks, metadata, memId)

            response = AgentResponse(
                transcript=self.text,
                chunks=chunks,
                metadata=metadata,
                userId=self.md.user_id,
                memoryId=memId
            )

            return response

        except Exception as e:
            TRACKER.update_status(
                user_id=self.md.user_id,
                document_id=memId,
                status=ProcessingStatus.FAILED,
                progress=100
            )
            raise RuntimeError(f"Error processing text: {str(e)}")

    async def store_memory_in_database(self, chunks: List[str], metadata: List[Metadata], memId: str) -> None:
        try:
            memories = []
            combined_memories = combine_data_chunks(chunks, metadata, memId)

            for i, chunk in enumerate(combined_memories):
                mem_data = {
                    "memId": memId,
                    "userId": self.md.user_id,
                    "chunkId": f"{memId}_{i}",
                    "title": self.md.title,
                    "memData": chunk["memData"],
                    "memType": 'note',
                    "source": self.md.source,
                    "tags": self.md.tags,
                    "metadata": chunk["metadata"],
                }
                memories.append(mem_data)

            # Insert memories in batches
            batch_size = 100
            for i in range(0, len(memories), batch_size):
                batch = memories[i:i + batch_size]
                await insert_many_memories_to_db(batch)

        except Exception as e:
            raise RuntimeError(
                f"Error storing text memory in database: {str(e)}")
