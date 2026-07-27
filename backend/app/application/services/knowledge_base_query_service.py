"""
File: app/application/services/knowledge_base_query_service.py
Folder: backend/app/application/services
Purpose: Read-side operations on a knowledge base collection: semantic
         search (embed query -> vector similarity) and structural browsing
         (list domains/controls without needing a query embedding at all).
"""

from collections import defaultdict

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.domain.ports.embedding_provider import EmbeddingProviderPort
from app.domain.ports.vector_store import VectorDocument, VectorStorePort

# get_documents() calls are capped so a huge collection can't be pulled in one shot
BROWSE_FETCH_LIMIT = 5000


class KnowledgeBaseQueryService:
    def __init__(self, vector_store: VectorStorePort, embedding_provider: EmbeddingProviderPort) -> None:
        self._vector_store = vector_store
        self._embeddings = embedding_provider

    def _resolve_collection(self, collection_name: str | None) -> str:
        name = collection_name or get_settings().DEFAULT_KB_COLLECTION_NAME
        if not self._vector_store.collection_exists(name):
            raise NotFoundError(f"Knowledge base collection '{name}' not found.")
        return name

    def search(
        self,
        query: str,
        collection_name: str | None = None,
        top_k: int = 5,
        domain: str | None = None,
    ) -> list[VectorDocument]:
        name = self._resolve_collection(collection_name)
        vector = self._embeddings.embed_query(query)
        where = {"domain": domain} if domain else None
        return self._vector_store.query(name, vector, top_k=top_k, where=where)

    def list_domains(self, collection_name: str | None = None) -> dict[str, int]:
        """Distinct domains present in a collection, with chunk counts."""
        name = self._resolve_collection(collection_name)
        docs = self._vector_store.get_documents(name, limit=BROWSE_FETCH_LIMIT)
        counts: dict[str, int] = defaultdict(int)
        for doc in docs:
            counts[str(doc.metadata.get("domain", "OTHER"))] += 1
        return dict(counts)

    def list_controls(self, collection_name: str | None = None, domain: str | None = None) -> list[dict]:
        """Distinct controls (control_parent chunks only) for a domain, or
        all domains if none given."""
        name = self._resolve_collection(collection_name)
        where = {"domain": domain} if domain else None
        docs = self._vector_store.get_documents(name, where=where, limit=BROWSE_FETCH_LIMIT)
        controls = []
        for doc in docs:
            if doc.metadata.get("sub_label") == "parent":
                controls.append(
                    {
                        "control_number": doc.metadata.get("clause", ""),
                        "title": doc.metadata.get("title", ""),
                        "domain": doc.metadata.get("domain", ""),
                        "sheet": doc.metadata.get("sheet", ""),
                    }
                )
        controls.sort(key=lambda c: c["control_number"])
        return controls

    def collection_stats(self, collection_name: str | None = None) -> dict:
        name = self._resolve_collection(collection_name)
        return {"collection": name, "total_chunks": self._vector_store.count(name)}
