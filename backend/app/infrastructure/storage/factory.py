"""
File: app/infrastructure/storage/factory.py
Folder: backend/app/infrastructure/storage
Purpose: Picks the file-storage adapter from STORAGE_PROVIDER in .env.
         Only local disk today; adding S3/MinIO means one adapter + one line.
"""

from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.domain.ports.file_storage import FileStoragePort
from app.infrastructure.storage.local_file_storage import LocalFileStorage

_PROVIDERS = ("local",)


def build_file_storage() -> FileStoragePort:
    settings = get_settings()
    provider = getattr(settings, "STORAGE_PROVIDER", "local").lower()
    if provider == "local":
        return LocalFileStorage(settings.EVIDENCE_STORAGE_PATH)
    raise ValidationError(
        f"Unsupported STORAGE_PROVIDER '{provider}'. Supported: {', '.join(_PROVIDERS)}."
    )