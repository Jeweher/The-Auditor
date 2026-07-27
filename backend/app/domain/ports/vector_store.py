"""
File: app/domain/ports/vector_store.py
Folder: backend/app/domain/ports
Purpose: Defines the contract every vector store adapter must implement.
         Application/service code depends ONLY on this interface, never on
         chromadb directly. Swapping to Qdrant/Pinecone/Weaviate/Milvus later
         means writing one new class in infrastructure/vector_store/ that
         implements this port — no other code changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class VectorDocument:
    """A single retrievable chunk stored in / returned from the vector store."""

    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: Optional[float] = None  # similarity score, populated on query results only


class VectorStorePort(ABC):
    """Abstract interface for any vector database backend."""

    @abstractmethod
    def collection_exists(self, collection_name: str) -> bool:
        """Return True if the named collection already exists."""
        raise NotImplementedError

    @abstractmethod
    def create_collection(self, collection_name: str) -> None:
        """Create a new, empty collection. No-op if it already exists."""
        raise NotImplementedError

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection and all its documents."""
        raise NotImplementedError

    @abstractmethod
    def list_collections(self) -> list[str]:
        """Return the names of all collections currently stored."""
        raise NotImplementedError

    @abstractmethod
    def add_documents(
        self,
        collection_name: str,
        documents: list[VectorDocument],
        embeddings: list[list[float]],
    ) -> None:
        """Add documents with their precomputed embeddings to a collection."""
        raise NotImplementedError

    @abstractmethod
    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: Optional[dict[str, Any]] = None,
    ) -> list[VectorDocument]:
        """Return the top_k most similar documents to query_embedding.

        `where` is an optional metadata filter (e.g. {"domain": "1"}).
        """
        raise NotImplementedError

    @abstractmethod
    def count(self, collection_name: str) -> int:
        """Return the number of documents stored in a collection."""
        raise NotImplementedError

    @abstractmethod
    def get_documents(
        self,
        collection_name: str,
        where: Optional[dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[VectorDocument]:
        """Fetch documents by metadata filter (no similarity search) — used
        to browse/list content (e.g. all chunks for one domain/control)
        rather than to search by meaning."""
        raise NotImplementedError
