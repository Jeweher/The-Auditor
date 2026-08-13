"""
File: app/application/services/auth_service.py
Folder: backend/app/application/services
Purpose: Business logic for registration, login, token refresh, and logout.
         Depends only on UserRepositoryPort — no direct DB or framework
         imports, so it's fully unit-testable with a fake repository.
"""

import hashlib
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domain.entities.user import User
from app.domain.ports.user_repository import UserRepositoryPort


def _hash_token(token: str) -> str:
    # Refresh tokens are stored hashed (like passwords) so a DB leak doesn't
    # expose usable tokens directly.
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(self, user_repository: UserRepositoryPort):
        self._repo = user_repository

    def register(
        self,
        email: str,
        password: str,
        full_name: str,
        company_name: str | None = None,
        sector: str | None = None,
        job_title: str | None = None,
        company_size: str | None = None,
        audit_reason: str | None = None,
    ) -> User:
        if self._repo.get_by_email(email) is not None:
            raise ConflictError("An account with this email already exists.")
        hashed = hash_password(password)
        return self._repo.create(
            email=email,
            hashed_password=hashed,
            full_name=full_name,
            company_name=company_name,
            sector=sector,
            job_title=job_title,
            company_size=company_size,
            audit_reason=audit_reason,
        )

    def update_profile(
        self,
        user_id,
        full_name: str | None = None,
        company_name: str | None = None,
        sector: str | None = None,
        job_title: str | None = None,
        company_size: str | None = None,
        audit_reason: str | None = None,
    ) -> User:
        return self._repo.update_profile(
            user_id,
            full_name=full_name,
            company_name=company_name,
            sector=sector,
            job_title=job_title,
            company_size=company_size,
            audit_reason=audit_reason,
        )

    def authenticate(self, email: str, password: str) -> User:
        user = self._repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password.")
        if not user.is_active:
            raise UnauthorizedError("This account has been deactivated.")
        if not user.email_verified:
            raise UnauthorizedError("Please verify your email address before logging in.")

        # One-time bootstrap: the configured admin email is promoted on its
        # first successful login. Purely additive — never demotes anyone,
        # and does nothing once that account is already an admin.
        settings = get_settings()
        bootstrap_email = settings.ADMIN_BOOTSTRAP_EMAIL.strip().lower()
        if bootstrap_email and user.email.strip().lower() == bootstrap_email and user.role != "admin":
            user = self._repo.set_role(user.id, "admin")

        return user

    def issue_tokens(self, user: User) -> tuple[str, str]:
        settings = get_settings()
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        self._repo.store_refresh_token(user.id, _hash_token(refresh_token), expires_at)

        return access_token, refresh_token

    def refresh_access_token(self, refresh_token: str) -> tuple[str, str]:
        payload = decode_token(refresh_token, expected_type="refresh")
        user_id = payload["sub"]

        from uuid import UUID  # local import avoids polluting module namespace

        user = self._repo.get_by_id(UUID(user_id))
        if user is None:
            raise UnauthorizedError("User no longer exists.")

        if not self._repo.is_refresh_token_valid(user.id, _hash_token(refresh_token)):
            raise UnauthorizedError("Refresh token is invalid, expired, or has been revoked.")

        # Rotate: revoke the used refresh token, issue a fresh pair.
        self._repo.revoke_refresh_token(user.id, _hash_token(refresh_token))
        return self.issue_tokens(user)

    def logout(self, user_id, refresh_token: str) -> None:
        self._repo.revoke_refresh_token(user_id, _hash_token(refresh_token))

    def get_current_user(self, access_token: str) -> User:
        from uuid import UUID

        payload = decode_token(access_token, expected_type="access")
        user = self._repo.get_by_id(UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found or inactive.")
        return user
    def update_profile_photo(self, user_id, content: bytes, mime_type: str) -> User:
        from app.infrastructure.media.profile_photo import process_profile_photo

        data_url = process_profile_photo(content, mime_type)
        return self._repo.set_profile_photo(user_id, data_url)

    def remove_profile_photo(self, user_id) -> User:
        return self._repo.set_profile_photo(user_id, None)
