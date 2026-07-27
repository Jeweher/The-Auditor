"""
File: app/infrastructure/storage/local_file_storage.py
Folder: backend/app/infrastructure/storage
Purpose: FileStoragePort backed by local disk. In Docker the base directory
         is a mounted volume (./data/evidence on the host), so uploaded files
         survive container restarts and rebuilds exactly like the Postgres
         and Chroma volumes already do.

         Keys are relative paths like "assessment_<id>/control_<n>/<file>".
         Path traversal is blocked so a crafted key cannot escape the base
         directory.
"""

import logging
from pathlib import Path

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.ports.file_storage import FileStoragePort

logger = logging.getLogger(__name__)


class LocalFileStorage(FileStoragePort):
    def __init__(self, base_path: str) -> None:
        self._base = Path(base_path).resolve()
        self._base.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        # Reject absolute keys and traversal before touching the filesystem.
        candidate = (self._base / key).resolve()
        if not str(candidate).startswith(str(self._base)):
            raise ValidationError("Invalid storage key.")
        return candidate

    def save(self, key: str, content: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        logger.info("Stored evidence at %s (%d bytes)", key, len(content))
        return str(path)

    def load(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.is_file():
            raise NotFoundError("Evidence file not found in storage.")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.is_file():
            path.unlink()
            logger.info("Deleted evidence at %s", key)

    def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()