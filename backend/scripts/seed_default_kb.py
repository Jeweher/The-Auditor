"""
File: scripts/seed_default_kb.py
Folder: backend/scripts
Purpose: One-shot script that populates the default ChromaDB collection
         (settings.DEFAULT_KB_COLLECTION_NAME, "tisax_kb_final") from the
         already-processed corpus JSON produced by the original Colab
         pipeline (all_corpus_final__7_.json -> data/all_corpus_final.json).

         Run once, manually, after `docker compose up -d postgres chromadb`:

             cd backend
             python -m scripts.seed_default_kb

         Safe to re-run: it replaces the collection rather than appending to
         it, so duplicate runs don't double the data. This script — and only
         this script — is allowed to write to the default collection;
         the /upload API endpoint refuses to target it.
"""

import json
import logging
import sys
from pathlib import Path

# Make `app` importable when running as `python -m scripts.seed_default_kb` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings  # noqa: E402
from app.core.logging_config import configure_logging  # noqa: E402
from app.infrastructure.embeddings.labse_embedding_provider import LaBSEEmbeddingProvider  # noqa: E402
from app.infrastructure.vector_store.chroma_store import ChromaVectorStore  # noqa: E402
from app.application.services.knowledge_base_ingestion_service import (  # noqa: E402
    KnowledgeBaseIngestionService,
)

CORPUS_PATH = Path(__file__).resolve().parent.parent / "data" / "all_corpus_final.json"

configure_logging()
logger = logging.getLogger("seed_default_kb")


def main() -> None:
    settings = get_settings()

    if not CORPUS_PATH.exists():
        logger.error("Corpus file not found at %s", CORPUS_PATH)
        sys.exit(1)

    logger.info("Loading corpus from %s", CORPUS_PATH)
    raw_chunks = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    logger.info("Loaded %d raw chunks", len(raw_chunks))

    vector_store = ChromaVectorStore()
    embeddings = LaBSEEmbeddingProvider()
    ingestion = KnowledgeBaseIngestionService(vector_store, embeddings)

    collection_name = settings.DEFAULT_KB_COLLECTION_NAME
    logger.info("Seeding collection '%s' (replacing if it already exists)...", collection_name)

    total = ingestion.ingest_raw_chunks(collection_name, raw_chunks, replace=True)

    logger.info("Done. %d chunks indexed in '%s'.", total, collection_name)
    logger.info("Verify via: GET /api/v1/knowledge-base/stats?collection=%s", collection_name)


if __name__ == "__main__":
    main()
