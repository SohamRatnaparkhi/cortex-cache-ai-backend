from pydantic import BaseModel

from app.schemas.Metadata import Metadata, NotionSpecificMd


class NotionRequest(BaseModel):
    page_id: str
    access_token: str
    metadata: Metadata[NotionSpecificMd]
