"""
File: app/domain/entities/user.py
Folder: backend/app/domain/entities
Purpose: Plain domain representation of a User, independent of SQLAlchemy or
         Pydantic. Services operate on this type; the ORM model and API
         schema are both mapped to/from it at the boundaries.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    id: UUID
    email: str
    hashed_password: str
    full_name: str
    is_active: bool
    created_at: datetime
    company_name: str | None = None
    sector: str | None = None
    profile_photo: str | None = None
    email_verified: bool = False
    role: str = "user"