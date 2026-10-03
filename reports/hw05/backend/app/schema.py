from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

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