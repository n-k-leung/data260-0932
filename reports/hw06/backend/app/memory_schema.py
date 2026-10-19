from typing import Optional
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    session_id: Optional[str] = None
    message: str = Field(min_length=1, max_length=4000)