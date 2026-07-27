"""
File: app/infrastructure/vector_store/chroma_store.py
Folder: backend/app/infrastructure/vector_store
Purpose: Concrete VectorStorePort implementation backed by a ChromaDB server
         (running as its own container, connected over HTTP). This is the
         ONLY file in the codebase that imports chromadb directly.
"""

import logging
from typing import Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.domain.ports.vector_store import VectorDocument, VectorStorePort

logger = logging.getLogger(__name__)


class ChromaVectorStore(VectorStorePort):
    def __init__(self) -> None:
        settings = get_settings()
        try:
            self._client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        except Exception as exc:  # connection-time failures
            logger.exception("Failed to initialize ChromaDB client")
            raise ExternalServiceError("Could not connect to the vector store.") from exc

    def collection_exists(self, collection_name: str) -> bool:
        try:
            existing = {c.name for c in self._client.list_collections()}
            return collection_name in existing
        except Exception as exc:
            logger.exception("Failed to check collection existence: %s", collection_name)
            raise ExternalServiceError("Vector store lookup failed.") from exc

    def create_collection(self, collection_name: str) -> None:
        try:
            self._client.get_or_create_collection(name=collection_name)
            logger.info("Ensured collection exists: %s", collection_name)
        except Exception as exc:
            logger.exception("Failed to create collection: %s", collection_name)
            raise ExternalServiceError("Vector store collection creation failed.") from exc

    def delete_collection(self, collection_name: str) -> None:
        try:
            self._client.delete_collection(name=collection_name)
            logger.info("Deleted collection: %s", collection_name)
        except Exception as exc:
            logger.exception("Failed to delete collection: %s", collection_name)
            raise ExternalServiceError("Vector store collection deletion failed.") from exc

    def list_collections(self) -> list[str]:
        try:
            return [c.name for c in self._client.list_collections()]
        except Exception as exc:
            logger.exception("Failed to list collections")
            raise ExternalServiceError("Vector store lookup failed.") from exc

    def add_documents(
        self,
        collection_name: str,
        documents: list[VectorDocument],
        embeddings: list[list[float]],
    ) -> None:
        if len(documents) != len(embeddings):
            raise ValueError("documents and embeddings must be the same length")
        if not documents:
            return
        try:
            collection = self._client.get_or_create_collection(name=collection_name)
            collection.add(
                ids=[doc.id for doc in documents],
                documents=[doc.content for doc in documents],
                metadatas=[doc.metadata for doc in documents],
                embeddings=embeddings,
            )
            logger.info("Added %d documents to collection %s", len(documents), collection_name)
        except Exception as exc:
            logger.exception("Failed to add documents to collection: %s", collection_name)
            raise ExternalServiceError("Vector store insert failed.") from exc

    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: Optional[dict[str, Any]] = None,
    ) -> list[VectorDocument]:
        try:
            collection = self._client.get_collection(name=collection_name)
            result = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
            )
        except Exception as exc:
            logger.exception("Query failed on collection: %s", collection_name)
            raise ExternalServiceError("Vector store query failed.") from exc

        documents: list[VectorDocument] = []
        ids = result.get("ids", [[]])[0]
        contents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0] if result.get("distances") else [None] * len(ids)

        for doc_id, content, metadata, distance in zip(ids, contents, metadatas, distances):
            documents.append(
                VectorDocument(
                    id=doc_id,
                    content=content,
                    metadata=metadata or {},
                    score=distance,
                )
            )
        return documents

    def count(self, collection_name: str) -> int:
        try:
            collection = self._client.get_collection(name=collection_name)
            return collection.count()
        except Exception as exc:
            logger.exception("Failed to count collection: %s", collection_name)
            raise ExternalServiceError("Vector store lookup failed.") from exc

    def get_documents(
        self,
        collection_name: str,
        where: Optional[dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[VectorDocument]:
        try:
            collection = self._client.get_collection(name=collection_name)
            result = collection.get(where=where, limit=limit, offset=offset)
        except Exception as exc:
            logger.exception("get_documents failed on collection: %s", collection_name)
            raise ExternalServiceError("Vector store lookup failed.") from exc

        ids = result.get("ids", [])
        contents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        return [
            VectorDocument(id=doc_id, content=content or "", metadata=metadata or {})
            for doc_id, content, metadata in zip(ids, contents, metadatas)
        ]
