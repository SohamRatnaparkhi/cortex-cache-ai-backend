import uuid
from typing import List

from app.core.agents.integrations.IntegrationAgent import IntegrationAgent
from app.core.jina_ai import use_jina
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import NotionSpecificMd
from app.services.MemoryService import insert_many_memories_to_db
from app.services.NotionPageExtractor import NotionTextExtractor
from app.utils.app_logger_config import logger
from app.utils.status_tracking import TRACKER, ProcessingStatus


class NotionAgent(IntegrationAgent[NotionSpecificMd]):
    async def process_media(self):
        page_id = self.resource_link
        access_token = self.access_token
        md = self.md
        memId = str(uuid.uuid4())

        TRACKER.create_status(md.user_id, memId, "Notion page")

        # Process the Notion page and get text from it
        content = NotionTextExtractor(page_id, access_token).get_page_content()

        TRACKER.update_status(
            md.user_id, memId, ProcessingStatus.CREATING_EMBEDDINGS, progress=25)

        chunks = use_jina.segment_data(content)

        self.md.memId = memId

        meta_chunks = []
        for i in range(len(chunks)):
            tmd = NotionSpecificMd(
                chunk_id=f'{memId}_{i}',
                page_id=page_id,
            )
            md_copy = self.md.model_copy()
            md_copy.specific_desc = tmd
            meta_chunks.append(md_copy)

        preprocessed_chunks = await self.embed_and_store_chunks(chunks, meta_chunks)

        TRACKER.update_status(
            md.user_id, memId, ProcessingStatus.STORING_DOCUMENT, progress=85)
        await self.store_memory_in_database(chunks=chunks, preprocessed_chunks=preprocessed_chunks, meta_chunks=meta_chunks, memId=memId)

        TRACKER.update_status(
            md.user_id, memId, ProcessingStatus.COMPLETED, progress=100)

        return AgentResponse(
            chunks=chunks,
            metadata=meta_chunks,
            transcript=content,
            userId=md.user_id,
            memoryId=memId
        )

    async def store_memory_in_database(self, chunks: List[str], preprocessed_chunks: List[str], meta_chunks: List[NotionSpecificMd], memId: str):
        try:
            memories = []
            for i, (chunk, meta) in enumerate(zip(chunks, meta_chunks)):
                mem_data = {
                    "memId": memId,
                    "userId": self.md.user_id,
                    "chunkId": f"{memId}_{i}",
                    "title": self.md.title,
                    "memData": chunk,
                    "memType": 'notion',
                    "source": self.md.source,
                    "tags": self.md.tags,
                    "metadata": meta.json(),
                }
                memories.append(mem_data)

            batch_size = 100
            for i in range(0, len(memories), batch_size):
                batch = memories[i:i + batch_size]
                await insert_many_memories_to_db(batch, preprocessed_chunks[i:i + batch_size])

        except Exception as e:
            raise RuntimeError(
                f"Error storing Web memory in database: {str(e)}")
