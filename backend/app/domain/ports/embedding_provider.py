"""
File: app/domain/ports/embedding_provider.py
Folder: backend/app/domain/ports
Purpose: Abstraction over whatever model turns text into vectors. Application
         code depends only on this interface, never on sentence_transformers
         directly — swapping LaBSE for another model, or a hosted embeddings
         API, means writing one new adapter in infrastructure/embeddings/.
"""

from abc import ABC, abstractmethod


class EmbeddingProviderPort(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector size produced by this provider."""
        raise NotImplementedError

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of chunk texts for storage."""
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single user query for similarity search."""
        raise NotImplementedError
