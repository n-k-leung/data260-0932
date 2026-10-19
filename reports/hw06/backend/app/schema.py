from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional, Literal

class UserCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=1)

class UserUpdate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email:EmailStr
    password:str

class VulCreate(BaseModel):
    package_name: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    vul_code: str = Field(min_length=1)
    vendor_id: int

class VulUpdate(BaseModel):
    package_name: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    vul_code: str = Field(min_length=1)
    vendor_id: int

class VulOut(BaseModel):
    id: int
    package_name: str
    severity: str
    vul_code: str
    report_count: int
    vendor_id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
        
class AdviOut (BaseModel):
    id: int
    fix_version: str

    class Config:
        from_attributes = True

class VulAdvi(BaseModel):
    id: int
    package_name: str
    severity: str
    advisories: list[AdviOut]

class VendorCreate(BaseModel):
    name: str = Field(min_length=1)
    industry: str = Field(min_length=1)
    contact_email: EmailStr

class VendorUpdate(VendorCreate):
    pass

class VendorOut(BaseModel):
    id: int
    name: str
    industry: str
    contact_email: EmailStr
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

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