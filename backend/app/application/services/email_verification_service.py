"""
File: app/application/services/email_verification_service.py
Folder: backend/app/application/services
Purpose: Business logic for the 6-digit email verification flow:
         generating/hashing codes, sending them, verifying with an
         attempt counter, and resending. Depends only on ports — no
         direct DB or framework imports — same principle as AuthService.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ExternalServiceError, NotFoundError, ValidationError
from app.domain.entities.user import User
from app.domain.ports.email_sender import EmailSenderPort
from app.domain.ports.email_verification_repository import EmailVerificationRepositoryPort
from app.domain.ports.user_repository import UserRepositoryPort

logger = logging.getLogger(__name__)


def _hash_code(code: str) -> str:
    # Same principle as refresh tokens (see auth_service._hash_token): the
    # raw code is never stored, only its hash.
    return hashlib.sha256(code.encode()).hexdigest()


def _generate_code() -> str:
    # Cryptographically random 6-digit code, zero-padded (e.g. "004821").
    return f"{secrets.randbelow(1_000_000):06d}"


class EmailVerificationService:
    def __init__(
        self,
        user_repository: UserRepositoryPort,
        verification_repository: EmailVerificationRepositoryPort,
        email_sender: EmailSenderPort,
    ):
        self._users = user_repository
        self._verifications = verification_repository
        self._email_sender = email_sender

    def send_verification_code(self, user: User) -> None:
        settings = get_settings()
        # Only one active code per user: discard any previous one first.
        self._verifications.invalidate_active_for_user(user.id)

        code = _generate_code()
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES
        )
        self._verifications.create(
            user_id=user.id,
            hashed_code=_hash_code(code),
            expires_at=expires_at,
            max_attempts=settings.EMAIL_VERIFICATION_MAX_ATTEMPTS,
        )

        try:
            self._email_sender.send(
                to=user.email,
                subject="Confirmez votre adresse email — The Auditor",
                html_body=self._build_email_html(
                    user.full_name, code, settings.EMAIL_VERIFICATION_EXPIRE_MINUTES
                ),
            )
        except Exception as exc:
            logger.error("Failed to send verification email to %s: %s", user.email, exc)
            raise ExternalServiceError(
                "We couldn't send the verification email. Please try again in a moment."
            ) from exc

    def verify_code(self, user_id: UUID, code: str) -> User:
        verification = self._verifications.get_active_for_user(user_id)
        if verification is None:
            raise NotFoundError("No verification code found. Please request a new one.")

        if verification.expires_at < datetime.now(timezone.utc):
            raise ValidationError("This code has expired. Please request a new one.")

        if verification.attempts >= verification.max_attempts:
            raise ValidationError("Too many incorrect attempts. Please request a new code.")

        if _hash_code(code) != verification.hashed_code:
            updated = self._verifications.increment_attempts(verification.id)
            remaining = updated.max_attempts - updated.attempts
            if remaining <= 0:
                raise ValidationError("Too many incorrect attempts. Please request a new code.")
            raise ValidationError(f"Incorrect code. {remaining} attempt(s) remaining.")

        self._verifications.mark_consumed(verification.id)
        return self._users.set_email_verified(user_id, True)

    def resend_code(self, email: str) -> User:
        user = self._users.get_by_email(email)
        if user is None:
            raise NotFoundError("No account found for this email.")
        if user.email_verified:
            raise ConflictError("This email is already verified.")
        self.send_verification_code(user)
        return user

    @staticmethod
    def _build_email_html(full_name: str, code: str, expire_minutes: int) -> str:
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
          <h2 style="color: #1fa3a6;">The Auditor</h2>
          <p>Bonjour {full_name},</p>
          <p>Voici votre code de confirmation :</p>
          <p style="font-size: 32px; font-weight: bold; letter-spacing: 8px; text-align: center; color: #1fa3a6;">
            {code}
          </p>
          <p>Ce code expire dans {expire_minutes} minutes.</p>
          <p>Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.</p>
        </div>
        """