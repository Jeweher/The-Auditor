
"""
File: app/infrastructure/llm/anthropic_client.py
Folder: backend/app/infrastructure/llm
Purpose: Concrete LLMPort backed by the Anthropic Messages API. This is the
         ONLY file that knows the Anthropic request/response format.

         Uses httpx directly rather than the anthropic SDK to keep the
         dependency surface small — the Messages endpoint is a single POST.
"""

import logging

import httpx

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.domain.ports.llm_client import LLMPort

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
REQUEST_TIMEOUT_SECONDS = 60.0


class AnthropicLLMClient(LLMPort):
    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.LLM_API_KEY
        self._model = settings.LLM_MODEL
        self._default_max_tokens = settings.LLM_MAX_TOKENS

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        if not self._api_key or self._api_key.startswith("your_"):
            raise ExternalServiceError(
                "LLM_API_KEY is not configured. Set a real key in the .env file."
            )

        payload = {
            "model": self._model,
            "max_tokens": max_tokens or self._default_max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if temperature is not None:
            payload["temperature"] = temperature
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        try:
            response = httpx.post(
                ANTHROPIC_API_URL, json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS
            )
        except httpx.RequestError as exc:
            logger.exception("LLM request failed to reach the API")
            raise ExternalServiceError("Could not reach the LLM provider.") from exc

        if response.status_code != 200:
            logger.error("LLM API returned %s: %s", response.status_code, response.text[:500])
            raise ExternalServiceError(
                f"LLM provider returned an error (HTTP {response.status_code})."
            )

        data = response.json()
        blocks = data.get("content", [])
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        if not text.strip():
            raise ExternalServiceError("LLM returned an empty response.")
        return text