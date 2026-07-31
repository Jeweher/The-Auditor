"""
File: app/infrastructure/db/repositories/email_verification_repository.py
Folder: backend/app/infrastructure/db/repositories
Purpose: Concrete EmailVerificationRepositoryPort implementation using
         SQLAlchemy. Maps ORM models to/from the framework-free
         domain.entities.EmailVerification.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.email_verification import EmailVerification
from app.domain.ports.email_verification_repository import EmailVerificationRepositoryPort
from app.infrastructure.db.models import EmailVerificationModel


def _to_domain(model: EmailVerificationModel) -> EmailVerification:
    return EmailVerification(
        id=model.id,
        user_id=model.user_id,
        hashed_code=model.hashed_code,
        attempts=model.attempts,
        max_attempts=model.max_attempts,
        expires_at=model.expires_at,
        created_at=model.created_at,
        consumed_at=model.consumed_at,
    )


class SqlAlchemyEmailVerificationRepository(EmailVerificationRepositoryPort):
    def __init__(self, db: Session):
        self._db = db

    def create(
        self,
        user_id: UUID,
        hashed_code: str,
        expires_at: datetime,
        max_attempts: int = 5,
    ) -> EmailVerification:
        model = EmailVerificationModel(
            user_id=user_id,
            hashed_code=hashed_code,
            expires_at=expires_at,
            max_attempts=max_attempts,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _to_domain(model)

    def get_active_for_user(self, user_id: UUID) -> Optional[EmailVerification]:
        stmt = (
            select(EmailVerificationModel)
            .where(
                EmailVerificationModel.user_id == user_id,
                EmailVerificationModel.consumed_at.is_(None),
            )
            .order_by(EmailVerificationModel.created_at.desc())
        )
        model = self._db.execute(stmt).scalars().first()
        return _to_domain(model) if model else None

    def increment_attempts(self, verification_id: UUID) -> EmailVerification:
        model = self._db.get(EmailVerificationModel, verification_id)
        model.attempts += 1
        self._db.commit()
        self._db.refresh(model)
        return _to_domain(model)

    def mark_consumed(self, verification_id: UUID) -> EmailVerification:
        model = self._db.get(EmailVerificationModel, verification_id)
        model.consumed_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(model)
        return _to_domain(model)

    def invalidate_active_for_user(self, user_id: UUID) -> None:
        stmt = select(EmailVerificationModel).where(
            EmailVerificationModel.user_id == user_id,
            EmailVerificationModel.consumed_at.is_(None),
        )
        models = self._db.execute(stmt).scalars().all()
        now = datetime.now(timezone.utc)
        for model in models:
            model.consumed_at = now
        self._db.commit()