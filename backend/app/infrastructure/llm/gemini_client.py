"""
File: app/infrastructure/llm/gemini_client.py
Folder: backend/app/infrastructure/llm
Purpose: Concrete LLMPort backed by Google's Gemini API (AI Studio). This is
         the ONLY file that knows Gemini's request/response format.

         Demonstrates the point of LLMPort: Anthropic and Gemini have quite
         different wire formats (system prompt placement, response shape,
         auth header), yet both satisfy the same interface, so application
         code is untouched when switching via LLM_PROVIDER in .env.

         Free-tier note: AI Studio's free tier only exists on projects with
         billing DISABLED. Enabling Cloud Billing silently removes it.
"""

import logging

import httpx

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.domain.ports.llm_client import LLMPort

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
REQUEST_TIMEOUT_SECONDS = 60.0


class GeminiLLMClient(LLMPort):
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

        url = f"{GEMINI_API_BASE}/{self._model}:generateContent"
        # Gemini keeps the system prompt in its own top-level field, unlike
        # Anthropic's "system" key — same idea, different shape.
        generation_config: dict = {"maxOutputTokens": max_tokens or self._default_max_tokens}
        if temperature is not None:
            generation_config["temperature"] = temperature
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": generation_config,
        }
        headers = {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }

        try:
            response = httpx.post(
                url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS
            )
        except httpx.RequestError as exc:
            logger.exception("LLM request failed to reach the API")
            raise ExternalServiceError("Could not reach the LLM provider.") from exc

        if response.status_code != 200:
            logger.error("Gemini API returned %s: %s", response.status_code, response.text[:500])
            raise ExternalServiceError(
                f"LLM provider returned an error (HTTP {response.status_code})."
            )




        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            # Usually means the prompt was blocked by safety filters
            reason = data.get("promptFeedback", {}).get("blockReason", "unknown")
            raise ExternalServiceError(f"Gemini returned no candidates (reason: {reason}).")

        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)

        if not text.strip():
            # Gemini's thinking models spend maxOutputTokens on internal
            # reasoning before emitting any text. If the budget runs out
            # first, we get finishReason=MAX_TOKENS with zero visible output.
            # Reporting that plainly beats a downstream "no JSON" error that
            # points at the wrong layer.
            finish = candidate.get("finishReason", "UNKNOWN")
            usage = data.get("usageMetadata", {})
            if finish == "MAX_TOKENS":
                raise ExternalServiceError(
                    "Gemini hit the output token limit before producing any text "
                    f"(thinking tokens: {usage.get('thoughtsTokenCount', 'n/a')}). "
                    "Raise LLM_MAX_TOKENS or the per-call max_tokens."
                )
            raise ExternalServiceError(
                f"LLM returned an empty response (finishReason: {finish})."
            )
        return text