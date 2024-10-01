from typing import Optional

from pydantic import BaseModel


class AgentResponseWrapper(BaseModel):
    response = Optional[str]
    error = Optional[str]
