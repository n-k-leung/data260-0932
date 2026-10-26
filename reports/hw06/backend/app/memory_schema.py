from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=4000)
    short_term_n: int | None = Field(default=None, ge=1, le=200)
    policy: str | None = None
    run_label: str | None = None
