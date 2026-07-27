"""
File: app/domain/ports/file_storage.py
Folder: backend/app/domain/ports
Purpose: Abstraction over where evidence files physically live. Application
         code stores and retrieves bytes by key and never knows whether
         those bytes sit on local disk, MinIO, or S3.

         Today the only adapter is local disk (a Docker volume that survives
         restarts). The day the deployment needs object storage, we add one
         adapter (s3_file_storage.py) and switch STORAGE_PROVIDER in .env —
         no service, router, or business logic changes. Same pattern as
         LLMPort and VectorStorePort.
"""

from abc import ABC, abstractmethod


class FileStoragePort(ABC):
    @abstractmethod
    def save(self, key: str, content: bytes) -> str:
        """Persist bytes under key. Returns the stored location/path."""
        raise NotImplementedError

    @abstractmethod
    def load(self, key: str) -> bytes:
        """Read bytes back. Raises NotFoundError if the key is unknown."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove the object. No error if it is already gone."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        raise NotImplementedError