from app.core.agents.integrations.NotionAgent import NotionAgent
from app.schemas.Common import AgentResponse
from app.schemas.Metadata import Metadata, NotionSpecificMd


async def extract_text_from_notion_page(resource_link: str, access_token: str, metadata: Metadata[NotionSpecificMd]) -> AgentResponse:
    agent = NotionAgent(resource_link, access_token, metadata)
    return await agent.process_media()
