import os
from abc import ABC, abstractmethod
from typing import Generic, List, TypeVar

from dotenv import load_dotenv

from app.core.PineconeClient import PineconeClient
from app.core.voyage import voyage_client
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import GitSpecificMd, Metadata, NotionSpecificMd
from app.utils.app_logger_config import logger
from app.utils.chunk_processing import update_chunks
from app.utils.status_tracking import TRACKER, ProcessingStatus
from app.utils.Vectors import get_vectors

if (os.path.exists('.env')):
    load_dotenv()

T = TypeVar('T', NotionSpecificMd, GitSpecificMd)


class IntegrationAgent(ABC, Generic[T]):
    """
    Abstract base class for link agents that process different types of media.

    Attributes:
        resource_link (str): The URL of the resource to process.
        md (Metadata[T]): Metadata associated with the resource.
    """

    def __init__(self, resource_link: str, access_token: str, md: Metadata[T], refresh_token=None) -> None:
        super().__init__()
        self.resource_link = resource_link
        self.access_token = access_token
        self.md = md
        self.refresh_token = refresh_token

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
            TRACKER.update_status(
                self.md.user_id, self.md.memId, ProcessingStatus.CREATING_EMBEDDINGS, progress=25)
            preprocessed_chunks = await update_chunks(chunks=chunks, memoryId=self.md.memId, userId=self.md.user_id)

            title = self.md.title
            description = self.md.description
            preprocessed_chunks = [
                title + " " + description + " " + chunk for chunk in preprocessed_chunks]

            embeddings = voyage_client.get_embeddings(preprocessed_chunks)

            vectors = get_vectors(metadata, embeddings)

            batch_size = 100
            pinecone_client = PineconeClient()
            res = pinecone_client.upsert(vectors, batch_size)
            logger.debug(res)
            return preprocessed_chunks
        except Exception as e:
            raise RuntimeError(f"Error embedding and storing chunks: {str(e)}")
