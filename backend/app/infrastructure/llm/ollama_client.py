"""
File: app/infrastructure/llm/ollama_client.py
Folder: backend/app/infrastructure/llm
Purpose: Concrete LLMPort backed by a local Ollama instance running the
         finetuned Qwen model (tisax-qwen). This is the ONLY file that
         knows Ollama's request/response format — mirrors gemini_client.py
         and anthropic_client.py in structure so the three are easy to
         compare and swap via LLM_PROVIDER in .env.

         Ollama exposes a native API at POST /api/chat, returning a single
         JSON object (not streamed, since we pass "stream": false).
"""

import logging

import httpx

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.domain.ports.llm_client import LLMPort

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 120.0  # local inference on consumer hardware can be slow


class OllamaLLMClient(LLMPort):
    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._model = settings.OLLAMA_MODEL

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        url = f"{self._base_url}/api/chat"
        payload: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {},
        }
        if max_tokens is not None:
            # Ollama's equivalent of max_tokens is num_predict.
            payload["options"]["num_predict"] = max_tokens
        if temperature is not None:
            payload["options"]["temperature"] = temperature

        try:
            response = httpx.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        except httpx.RequestError as exc:
            logger.exception("Ollama request failed to reach the local server")
            raise ExternalServiceError(
                "Could not reach Ollama. Is it running locally (ollama serve)?"
            ) from exc

        if response.status_code != 200:
            logger.error("Ollama returned %s: %s", response.status_code, response.text[:500])
            raise ExternalServiceError(
                f"Ollama returned an error (HTTP {response.status_code})."
            )

        data = response.json()
        text = data.get("message", {}).get("content", "")

        if not text.strip():
            raise ExternalServiceError(
                f"Ollama returned an empty response (done_reason: {data.get('done_reason', 'unknown')})."
            )
        return text