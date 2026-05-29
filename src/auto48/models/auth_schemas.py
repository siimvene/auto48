"""Pydantic request/response schemas for authentication endpoints.

Kept separate from schemas.py to avoid merge conflicts with other agents'
changes to the listings/vehicle schemas.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from auto48.models.seller import SellerType


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str
    seller_type: SellerType


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
