from pydantic import BaseModel, Field, EmailStr

class UserCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr

class UserUpdate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr

    class Config:
        from_attributes = True

class VulCreate(BaseModel):
    package_name: str = Field(min_length=1)
    severity: str = Field(min_length=1)

class VulUpdate(BaseModel):
    package_name: str = Field(min_length=1)
    severity: str = Field(min_length=1)

class VulOut(BaseModel):
    package_name: str
    severity: str

    class Config:
        from_attributes = True