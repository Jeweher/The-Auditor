"""
File: app/application/schemas/auth.py
Folder: backend/app/application/schemas
Purpose: Request/response models for the auth API. Kept separate from
         domain entities so the API contract can evolve independently of
         internal representation.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    sector: str | None = Field(default=None, max_length=255)
    job_title: str | None = Field(default=None, max_length=100)
    company_size: str | None = Field(default=None, max_length=50)
    audit_reason: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    user_id: UUID
    code: str = Field(min_length=6, max_length=6)


class ResendVerificationRequest(BaseModel):
    email: EmailStr    


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    company_name: str | None = None
    sector: str | None = None
    profile_photo: str | None = None
    is_active: bool
    email_verified: bool
    role: str
    job_title: str | None = None
    company_size: str | None = None
    audit_reason: str | None = None
    job_title: str | None = None
    company_size: str | None = None
    audit_reason: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}



class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    company_name: str | None = None
    sector: str | None = None
    job_title: str | None = None
    company_size: str | None = None
    audit_reason: str | None = None    