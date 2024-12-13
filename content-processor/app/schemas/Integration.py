from typing import Optional

from pydantic import BaseModel

from app.schemas.Metadata import GDriveSpecificMd, Metadata, NotionSpecificMd


class NotionRequest(BaseModel):
    page_id: str
    access_token: str
    metadata: Metadata[NotionSpecificMd]


class GDriveRequest(BaseModel):
    file_id: str
    access_token: str
    refresh_token: Optional[str] = ""
    metadata: Metadata[GDriveSpecificMd]
