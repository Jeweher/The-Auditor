




"""
File: app/infrastructure/llm/factory.py
Folder: backend/app/infrastructure/llm
Purpose: Picks the LLM adapter based on LLM_PROVIDER in .env. Adding another
         provider means writing one adapter class and adding one line here —
         nothing in application/ changes.
"""

from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.domain.ports.llm_client import LLMPort
from app.infrastructure.llm.anthropic_client import AnthropicLLMClient
from app.infrastructure.llm.gemini_client import GeminiLLMClient
from app.infrastructure.llm.ollama_client import OllamaLLMClient

_PROVIDERS = {
    "anthropic": AnthropicLLMClient,
    "gemini": GeminiLLMClient,
    "ollama": OllamaLLMClient,

}


def build_llm_client() -> LLMPort:
    provider = get_settings().LLM_PROVIDER.lower()
    client_cls = _PROVIDERS.get(provider)
    if client_cls is None:
        raise ValidationError(
            f"Unsupported LLM_PROVIDER '{provider}'. Supported: {', '.join(sorted(_PROVIDERS))}."
        )
    return client_cls()