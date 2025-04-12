from pydantic import BaseModel, Field
from typing import Optional

class UserCreate(BaseModel):
    phone: str
    password : str
    sms_cod : str

class smsUser(BaseModel):
    phone: str
    password : str

class UserInDB(BaseModel):
    id: int
    phone: str

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class ProductCreate(BaseModel):
    name : str
    cost : float
    number : int

class ProductSchema(BaseModel):
    name : str
    cost : float
    number : int
    picture : Optional[str]

    class Config:
        orm_mode = True
