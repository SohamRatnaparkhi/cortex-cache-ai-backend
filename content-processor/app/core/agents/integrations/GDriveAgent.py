import uuid
from typing import List

from app.core.agents.integrations.IntegrationAgent import IntegrationAgent
from app.core.jina_ai import use_jina
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import GDriveFileType, GDriveSpecificMd
from app.services.MemoryService import insert_many_memories_to_db
from app.utils.drive_content_extractor import GDriveProcessor
from app.utils.status_tracking import TRACKER, ProcessingStatus


class DriveAgent(IntegrationAgent[GDriveSpecificMd]):
    async def process_media(self) -> AgentResponse:
        try:
            processor = GDriveProcessor(
                self.resource_link, self.access_token, self.refresh_token)
            file_type, file_metadata = processor.get_file_type()
            memId = str(uuid.uuid4())
            self.md.memId = memId
            TRACKER.create_status(self.md.user_id, memId, self.md.title)

            content = ""
            if file_type == GDriveFileType.GDOC:
                content = processor.extract_doc_content()
            elif file_type == GDriveFileType.GSHEET:
                content = processor.extract_sheet_content()
            elif file_type == GDriveFileType.GSLIDE:
                content = processor.extract_slide_content()
            elif file_type in [GDriveFileType.PDF, GDriveFileType.IMAGE,
                               GDriveFileType.AUDIO, GDriveFileType.VIDEO]:
                # Call your existing handlers for these types
                pass
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            # For text-based content (docs, sheets, slides)
            if content:
                chunks = use_jina.segment_data(content)
                self.md.memId = memId
                metadata = []

                for i, chunk in enumerate(chunks):
                    chunk_metadata = GDriveSpecificMd(
                        chunk_id=f"{memId}_{i}",
                        file_id=self.resource_link,
                        page_number=i,
                        sheet_name=None,
                    )
                    md_copy = self.md.model_copy()
                    md_copy.specific_desc = chunk_metadata
                    metadata.append(md_copy)

                processed_chunks = await self.embed_and_store_chunks(chunks, metadata)

                TRACKER.update_status(
                    self.md.user_id, memId, status=ProcessingStatus.STORING_DOCUMENT, progress=85)
                await self.store_memory_in_database(chunks=chunks, preprocessed_chunks=processed_chunks, meta_chunks=metadata, memId=memId)

                TRACKER.update_status(
                    self.md.user_id, memId, status=ProcessingStatus.COMPLETED, progress=100)
                return AgentResponse(
                    chunks=chunks,
                    metadata=metadata,
                    transcript=content,
                    userId=self.md.user_id,
                    memoryId=memId,
                )
        except Exception as e:
            TRACKER.update_status(
                self.md.user_id, memId, status=ProcessingStatus.FAILED, error=str(e))
            raise RuntimeError(f"Failed to process Drive file: {str(e)}")

    async def store_memory_in_database(self, chunks: List[str], preprocessed_chunks: List[str], meta_chunks: List[GDriveSpecificMd], memId: str):
        try:
            memories = []
            for i, (chunk, meta) in enumerate(zip(chunks, meta_chunks)):
                mem_data = {
                    "memId": memId,
                    "userId": self.md.user_id,
                    "chunkId": f"{memId}_{i}",
                    "title": self.md.title,
                    "memData": chunk,
                    "memType": 'drive',
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
            TRACKER.update_status(
                self.md.user_id, memId, status=ProcessingStatus.FAILED, error=str(e))
            raise RuntimeError(
                f"Error storing Web memory in database: {str(e)}")
