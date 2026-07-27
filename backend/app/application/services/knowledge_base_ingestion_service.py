"""
File: app/application/services/knowledge_base_ingestion_service.py
Folder: backend/app/application/services
Purpose: The single orchestration point for turning chunks into a queryable
         ChromaDB collection. Used by both:
           - scripts/seed_default_kb.py (default corpus, run once)
           - POST /api/v1/knowledge-base/upload (per-assessment Excel upload)
         Depends only on ports (VectorStorePort, EmbeddingProviderPort), so
         swapping the vector DB or the embedding model never touches this
         file.
"""

import logging

from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.domain.entities.knowledge_chunk import KnowledgeChunk
from app.domain.ports.embedding_provider import EmbeddingProviderPort
from app.domain.ports.vector_store import VectorDocument, VectorStorePort
from app.infrastructure.knowledge_base import excel_isa_parser
from app.infrastructure.knowledge_base.metadata_builder import chunks_to_knowledge_chunks

logger = logging.getLogger(__name__)

EMBED_BATCH_SIZE = 100


class KnowledgeBaseIngestionService:
    def __init__(self, vector_store: VectorStorePort, embedding_provider: EmbeddingProviderPort) -> None:
        self._vector_store = vector_store
        self._embeddings = embedding_provider

    def ingest_chunks(self, collection_name: str, chunks: list[KnowledgeChunk], replace: bool = False) -> int:
        """Embed and store a list of already-built KnowledgeChunk entities.
        Returns the number of chunks stored."""
        if not chunks:
            raise ValidationError("No chunks to ingest.")

        if replace and self._vector_store.collection_exists(collection_name):
            self._vector_store.delete_collection(collection_name)
        self._vector_store.create_collection(collection_name)

        total = 0
        for i in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch = chunks[i : i + EMBED_BATCH_SIZE]
            texts = [c.embedding_text for c in batch]
            vectors = self._embeddings.embed_documents(texts)
            documents = [
                VectorDocument(id=c.id, content=c.content, metadata=c.metadata) for c in batch
            ]
            self._vector_store.add_documents(collection_name, documents, vectors)
            total += len(batch)
            logger.info("Ingested %d/%d chunks into %s", total, len(chunks), collection_name)

        return total

    def ingest_raw_chunks(self, collection_name: str, raw_chunks: list[dict], replace: bool = False) -> int:
        """Convenience wrapper: convert raw parser-shaped dicts to
        KnowledgeChunk first (via the shared metadata builder), then ingest."""
        return self.ingest_chunks(collection_name, chunks_to_knowledge_chunks(raw_chunks), replace=replace)

    def ingest_excel_upload(self, collection_name: str, file_bytes: bytes, filename: str) -> int:
        """Full upload flow: validate + parse Excel -> chunk -> embed -> new
        collection. The caller (router) is responsible for choosing a
        collection name scoped to one assessment, and for never reusing the
        default collection name here."""
        settings_default = get_settings().DEFAULT_KB_COLLECTION_NAME
        if collection_name == settings_default:
            raise ValidationError("Cannot overwrite the default knowledge base via upload.")

        raw_chunks = excel_isa_parser.process_excel(file_bytes, filename)
        return self.ingest_raw_chunks(collection_name, raw_chunks, replace=True)
