from app.core.agents.integrations.GDriveAgent import DriveAgent
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import GDriveSpecificMd, Metadata


async def extract_text_from_drive_file(resource_link: str, access_token: str, metadata: Metadata[GDriveSpecificMd], refresh_token) -> AgentResponse:
    agent = DriveAgent(resource_link, access_token,
                       metadata, refresh_token=refresh_token)
    return await agent.process_media()
