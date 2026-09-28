from pydantic import BaseModel, Field, EmailStr

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

class VulUpdate(BaseModel):
    package_name: str = Field(min_length=1)
    severity: str = Field(min_length=1)

class VulOut(BaseModel):
    id: int
    package_name: str
    severity: str

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