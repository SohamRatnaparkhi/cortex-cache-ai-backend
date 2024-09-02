from typing import Union

from pydantic import BaseModel


class ProcessVideoRequest(BaseModel):
    video_id: str
    video_url: Union[str, None]
