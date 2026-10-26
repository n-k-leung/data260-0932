from typing import Optional, Literal
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    session_id: Optional[str] = None
    message: str = Field(min_length=1, max_length=4000)
    short_term_n: Optional[int] = Field(default=None, ge=1, le=200)
    policy: Optional[str] = None
    run_label:Optional[str] =None