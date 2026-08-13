"""
File: app/infrastructure/db/repositories/user_repository.py
Folder: backend/app/infrastructure/db/repositories
Purpose: Concrete UserRepositoryPort implementation using SQLAlchemy.
         Maps ORM models to/from the framework-free domain.entities.User.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.user import User
from app.domain.ports.user_repository import UserRepositoryPort
from app.infrastructure.db.models import RefreshTokenModel, UserModel


def _to_domain(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        hashed_password=model.hashed_password,
        full_name=model.full_name,
        is_active=model.is_active,
        created_at=model.created_at,
        company_name=model.company_name,
        sector=model.sector,
        profile_photo=model.profile_photo,
        email_verified=model.email_verified,
        role=model.role,
        job_title=model.job_title,
        company_size=model.company_size,
        audit_reason=model.audit_reason,
    )


class SqlAlchemyUserRepository(UserRepositoryPort):
    def __init__(self, db: Session):
        self._db = db

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        model = self._db.get(UserModel, user_id)
        return _to_domain(model) if model else None

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.email == email)
        model = self._db.execute(stmt).scalar_one_or_none()
        return _to_domain(model) if model else None

    def create(
        self,
        email: str,
        hashed_password: str,
        full_name: str,
        company_name: str | None = None,
        sector: str | None = None,
        job_title: str | None = None,
        company_size: str | None = None,
        audit_reason: str | None = None,
    ) -> User:
        model = UserModel(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            company_name=company_name,
            sector=sector,
            job_title=job_title,
            company_size=company_size,
            audit_reason=audit_reason,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return _to_domain(model)
    def set_profile_photo(self, user_id: UUID, data_url: str | None) -> User:
        model = self._db.get(UserModel, user_id)
        model.profile_photo = data_url
        self._db.commit()
        self._db.refresh(model)
        return _to_domain(model)
    def set_email_verified(self, user_id: UUID, verified: bool) -> User:
        model = self._db.get(UserModel, user_id)
        model.email_verified = verified
        self._db.commit()
        self._db.refresh(model)
        return _to_domain(model)
    def set_role(self, user_id: UUID, role: str) -> User:
        model = self._db.get(UserModel, user_id)
        model.role = role
        self._db.commit()
        self._db.refresh(model)
        return _to_domain(model)
    def update_profile(
        self,
        user_id: UUID,
        full_name: str | None = None,
        company_name: str | None = None,
        sector: str | None = None,
        job_title: str | None = None,
        company_size: str | None = None,
        audit_reason: str | None = None,
    ) -> User:
        model = self._db.get(UserModel, user_id)
        # Each field is only updated if explicitly provided (not None) —
        # this lets the endpoint accept a partial payload (edit just one
        # field) without accidentally blanking out the others.
        if full_name is not None:
            model.full_name = full_name
        if company_name is not None:
            model.company_name = company_name
        if sector is not None:
            model.sector = sector
        if job_title is not None:
            model.job_title = job_title
        if company_size is not None:
            model.company_size = company_size
        if audit_reason is not None:
            model.audit_reason = audit_reason
        self._db.commit()
        self._db.refresh(model)
        return _to_domain(model)
    def list_all(self) -> list[User]:
        models = self._db.query(UserModel).order_by(UserModel.created_at.desc()).all()
        return [_to_domain(m) for m in models]

    def set_active(self, user_id: UUID, is_active: bool) -> User:
        model = self._db.get(UserModel, user_id)
        model.is_active = is_active
        self._db.commit()
        self._db.refresh(model)
        return _to_domain(model)

    def store_refresh_token(self, user_id: UUID, hashed_token: str, expires_at: datetime) -> None:
        token_model = RefreshTokenModel(user_id=user_id, hashed_token=hashed_token, expires_at=expires_at)
        self._db.add(token_model)
        self._db.commit()

    def is_refresh_token_valid(self, user_id: UUID, hashed_token: str) -> bool:
        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.user_id == user_id,
            RefreshTokenModel.hashed_token == hashed_token,
            RefreshTokenModel.revoked.is_(False),
        )
        token_model = self._db.execute(stmt).scalar_one_or_none()
        if token_model is None:
            return False
        return token_model.expires_at > datetime.now(token_model.expires_at.tzinfo)

    def revoke_refresh_token(self, user_id: UUID, hashed_token: str) -> None:
        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.user_id == user_id,
            RefreshTokenModel.hashed_token == hashed_token,
        )
        token_model = self._db.execute(stmt).scalar_one_or_none()
        if token_model:
            token_model.revoked = True
            self._db.commit()
