"""
File: app/domain/ports/user_repository.py
Folder: backend/app/domain/ports
Purpose: Interface the AuthService depends on. The SQLAlchemy implementation
         lives in infrastructure/db/repositories/user_repository.py — swapping
         persistence technology later means implementing this interface again,
         nothing in application/services changes.
"""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities.user import User


class UserRepositoryPort(ABC):
    @abstractmethod
    def get_by_id(self, user_id: UUID) -> Optional[User]:
        raise NotImplementedError

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        raise NotImplementedError

    @abstractmethod
    def create(
        self,
        email: str,
        hashed_password: str,
        full_name: str,
        company_name: str | None = None,
        sector: str | None = None,
    ) -> User:
        raise NotImplementedError
    @abstractmethod
    def set_profile_photo(self, user_id: UUID, data_url: str | None) -> User:
        raise NotImplementedError
    @abstractmethod
    def set_email_verified(self, user_id: UUID, verified: bool) -> User:
        raise NotImplementedError

    @abstractmethod
    def store_refresh_token(self, user_id: UUID, hashed_token: str, expires_at) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_refresh_token_valid(self, user_id: UUID, hashed_token: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def revoke_refresh_token(self, user_id: UUID, hashed_token: str) -> None:
        raise NotImplementedError
