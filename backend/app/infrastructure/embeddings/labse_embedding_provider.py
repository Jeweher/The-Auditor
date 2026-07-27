"""
File: app/infrastructure/embeddings/labse_embedding_provider.py
Folder: backend/app/infrastructure/embeddings
Purpose: Concrete EmbeddingProviderPort backed by sentence-transformers/LaBSE
         — the same model used in the original Colab pipeline. This is the
         ONLY file that imports sentence_transformers directly.

         The model is loaded lazily and once per process (first call pays the
         load cost, ~1.8GB download + load into memory on CPU is fine on a
         mid-range machine; no GPU required). Reused as a singleton via
         get_embedding_provider() in api/v1/deps.py so it isn't reloaded per
         request.
"""

import logging
import time

from app.core.config import get_settings
from app.domain.ports.embedding_provider import EmbeddingProviderPort

logger = logging.getLogger(__name__)


class LaBSEEmbeddingProvider(EmbeddingProviderPort):
    def __init__(self) -> None:
        settings = get_settings()
        self._model_name = settings.EMBEDDING_MODEL_NAME
        self._model = None  # lazy-loaded on first use

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer  # heavy import, deferred

        logger.info("Loading embedding model: %s", self._model_name)
        t0 = time.time()
        self._model = SentenceTransformer(self._model_name)
        logger.info(
            "Embedding model loaded in %.1fs (dim=%d)",
            time.time() - t0,
            self._model.get_sentence_embedding_dimension(),
        )

    @property
    def dimension(self) -> int:
        self._ensure_loaded()
        return self._model.get_sentence_embedding_dimension()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self._ensure_loaded()
        if not texts:
            return []
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
