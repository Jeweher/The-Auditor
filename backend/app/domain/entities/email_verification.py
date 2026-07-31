"""
File: app/domain/entities/email_verification.py
Folder: backend/app/domain/entities
Purpose: Plain domain representation of an EmailVerification code, independent
         of SQLAlchemy. Mirrors the pattern used by User.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class EmailVerification:
    id: UUID
    user_id: UUID
    hashed_code: str
    attempts: int
    max_attempts: int
    expires_at: datetime
    created_at: datetime
    consumed_at: datetime | None = None