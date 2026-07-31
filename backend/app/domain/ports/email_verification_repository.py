"""
File: app/domain/ports/email_verification_repository.py
Folder: backend/app/domain/ports
Purpose: Interface the future EmailVerificationService depends on. The
         SQLAlchemy implementation lives in
         infrastructure/db/repositories/email_verification_repository.py.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.domain.entities.email_verification import EmailVerification


class EmailVerificationRepositoryPort(ABC):
    @abstractmethod
    def create(
        self,
        user_id: UUID,
        hashed_code: str,
        expires_at: datetime,
        max_attempts: int = 5,
    ) -> EmailVerification:
        raise NotImplementedError

    @abstractmethod
    def get_active_for_user(self, user_id: UUID) -> Optional[EmailVerification]:
        """Latest non-consumed verification row for this user, if any."""
        raise NotImplementedError

    @abstractmethod
    def increment_attempts(self, verification_id: UUID) -> EmailVerification:
        raise NotImplementedError

    @abstractmethod
    def mark_consumed(self, verification_id: UUID) -> EmailVerification:
        raise NotImplementedError

    @abstractmethod
    def invalidate_active_for_user(self, user_id: UUID) -> None:
        """Consume/discard any existing active codes before issuing a new one (resend)."""
        raise NotImplementedError