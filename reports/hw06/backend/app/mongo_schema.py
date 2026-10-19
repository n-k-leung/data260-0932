from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional, Literal

StatusType = Literal["open", "triaged", "fixed", "wont_fix"]
CategoryType = Literal["injection", "xss", "auth", "dos", "other"]

class VulDocCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    status: StatusType = "open"
    category: CategoryType
    discovered_at: datetime

class VulDocUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    status: Optional[StatusType] = None
    category: Optional[CategoryType] = None
    discovered_at: Optional[datetime] = None

class VulDocOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: StatusType
    category: CategoryType
    discovered_at: datetime
    created_at: datetime
    updated_at: datetime