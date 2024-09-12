from app.core.agents.MediaAgent import File_PDFAgent
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import MediaSpecificMd, Metadata


async def extract_text_from_pdf(s3_url: str, metadata: Metadata[MediaSpecificMd]) -> AgentResponse:
    agent = File_PDFAgent(s3_url, metadata)
    return await agent.process_media()