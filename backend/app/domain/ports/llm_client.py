"""
File: app/domain/ports/llm_client.py
Folder: backend/app/domain/ports
Purpose: Abstraction over whatever LLM answers our prompts. Application
         services depend only on this interface — never on a vendor SDK
         directly. Switching provider means writing one new adapter in
         infrastructure/llm/ and changing LLM_PROVIDER in .env; no business
         logic changes.
"""

from abc import ABC, abstractmethod


class LLMPort(ABC):
    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Send a single-turn prompt and return the model's text response.

        temperature=0 is used for scoring tasks (maturity estimation, answer
        classification) where the same input must yield the same output —
        a compliance tool that returns ML2 then ML3 for identical data is
        not defensible. None leaves the provider default.
        """
        raise NotImplementedError