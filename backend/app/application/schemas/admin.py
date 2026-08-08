"""
File: app/application/schemas/admin.py
Folder: backend/app/application/schemas
Purpose: Request/response models for admin-only endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AdminUserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    company_name: str | None = None
    sector: str | None = None
    role: str
    is_active: bool
    email_verified: bool
    created_at: datetime


class UpdateUserRoleRequest(BaseModel):
    role: str  # "user" | "admin"


class UpdateUserActiveRequest(BaseModel):
    is_active: bool