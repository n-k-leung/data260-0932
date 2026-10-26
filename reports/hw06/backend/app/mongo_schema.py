from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

StatusType = Literal["open", "triaged", "fixed", "wont_fix"]
CategoryType = Literal["injection", "xss", "auth", "dos", "other"]


class VulDocCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str | None = None
    status: StatusType = "open"
    category: CategoryType
    discovered_at: datetime


class VulDocUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    status: StatusType | None = None
    category: CategoryType | None = None
    discovered_at: datetime | None = None


class VulDocOut(BaseModel):
    id: str
    title: str
    description: str | None = None
    status: StatusType
    category: CategoryType
    discovered_at: datetime
    created_at: datetime
    updated_at: datetime
