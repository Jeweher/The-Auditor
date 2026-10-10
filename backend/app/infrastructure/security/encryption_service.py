"""
File: app/infrastructure/security/encryption_service.py
Folder: backend/app/infrastructure/security
Purpose: Symmetric encryption/decryption for sensitive stored data
         (evidence file contents and extracted text), using Fernet
         (AES-128-CBC + HMAC).
"""

from cryptography.fernet import Fernet, InvalidToken
from app.core.config import get_settings


class EncryptionService:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.ENCRYPTION_KEY:
            raise ValueError(
                "ENCRYPTION_KEY is not set in the environment (.env)."
            )
        self._fernet = Fernet(settings.ENCRYPTION_KEY.encode())

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string, returning a base64 ciphertext string."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string previously produced by encrypt()."""
        if not ciphertext:
            return ""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Invalid or corrupted encrypted data.") from exc

    def encrypt_bytes(self, data: bytes) -> bytes:
        """Encrypt raw bytes (e.g. an uploaded file's content)."""
        return self._fernet.encrypt(data)

    def decrypt_bytes(self, token: bytes) -> bytes:
        """Decrypt bytes previously produced by encrypt_bytes()."""
        try:
            return self._fernet.decrypt(token)
        except InvalidToken as exc:
            raise ValueError("Invalid or corrupted encrypted data.") from exc