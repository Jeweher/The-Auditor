"""
File: app/application/services/public_assistant_service.py
Folder: backend/app/application/services
Purpose: The public, unauthenticated "TISAX Teacher" — answers general
         questions about TISAX/VDA ISA for visitors who don't have an
         account yet. Grounded in the same knowledge base used for the
         audit engine, but with an educational tone instead of an
         auditor's tone, and short, plain-language answers.
"""

from app.application.services.knowledge_base_query_service import KnowledgeBaseQueryService
from app.domain.ports.llm_client import LLMPort

MAX_HISTORY_TURNS = 6
TOP_K_CHUNKS = 4

TEACHER_SYSTEM_PROMPT = """You are a friendly, knowledgeable TISAX / VDA ISA expert helping a visitor understand the standard — like a patient teacher, not an auditor.

Use the reference material below to ground your answer whenever it's relevant. If it doesn't cover the question, answer from general TISAX/VDA ISA knowledge but keep the same short, plain style.

Rules:
- Keep answers short: 2-4 sentences, plain language, no jargon dump.
- Naturally mention "the VDA ISA standard" or similar when your answer draws from the reference material — don't add a separate sources list.
- Be warm and conversational. If greeted, greet back briefly and offer to help.
- If asked something unrelated to TISAX, information security, or automotive compliance, politely say that's outside what you can help with here.
- Never invent specific clause numbers or maturity level definitions that aren't in the reference material.

REFERENCE MATERIAL:
{context}"""


class PublicAssistantService:
    def __init__(self, kb_query_service: KnowledgeBaseQueryService, llm: LLMPort) -> None:
        self._kb = kb_query_service
        self._llm = llm

    def answer(self, message: str, history: list[dict[str, str]] | None = None) -> str:
        chunks = self._kb.search(message, top_k=TOP_K_CHUNKS)
        context = "\n\n".join(f"- {c.content}" for c in chunks) or "(no directly relevant material found)"
        system_prompt = TEACHER_SYSTEM_PROMPT.format(context=context)

        trimmed_history = (history or [])[-MAX_HISTORY_TURNS:]
        history_text = "\n".join(f"{h['role']}: {h['content']}" for h in trimmed_history)
        user_prompt = (
            (f"Conversation so far:\n{history_text}\n\n" if history_text else "")
            + f"Visitor's new message: {message}"
        )

        return self._llm.complete(system_prompt, user_prompt, max_tokens=400).strip()