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

    def __init__(self, resource_link: str, access_token: str, md: Metadata[T]) -> None:
        super().__init__()
        self.resource_link = resource_link
        self.access_token = access_token
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
            preprocessed_chunks = await update_chunks(chunks=chunks)

            title = self.md.title
            description = self.md.description

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
            return preprocessed_chunks
        except Exception as e:
            raise RuntimeError(f"Error embedding and storing chunks: {str(e)}")
