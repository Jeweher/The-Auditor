"""
File: app/application/services/recommendation_service.py
Folder: backend/app/application/services
Purpose: Generates the auditor-style recommendation for one control, based on
         its assessed maturity, the target, the evidence situation, and what
         is missing to reach the next level. Deterministic templates cover the
         clear-cut cases (no gap, missing evidence, contradicted evidence) so
         the LLM is only used where a tailored suggestion adds value — and at
         temperature 0 for reproducibility.
"""

import logging

from app.domain.ports.llm_client import LLMPort

logger = logging.getLogger(__name__)


RECOMMENDATION_SYSTEM_PROMPT = """You are a TISAX / VDA ISA assessor writing a concise, actionable recommendation for one control.

You are given the control, its assessed maturity level, the target, the evidence situation, and what is missing to reach the next level.

Write ONE short recommendation (1-2 sentences) telling the organisation what concrete action closes the gap. Be specific and practical. No preamble. Same language as the control text (default English).

Respond with ONLY the recommendation text, no JSON, no quotes."""


class RecommendationService:
    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def generate(
        self,
        control_number: str,
        control_title: str,
        maturity_level: int,
        target: int,
        evidence_status: str,
        missing_for_next_level: str,
    ) -> str:
        # Deterministic shortcuts — no LLM needed for the obvious cases.
        if maturity_level >= target:
            if evidence_status in ("missing",):
                return (
                    "Target maturity is met based on your declaration. Upload supporting "
                    "evidence to move this control from a declared to a verified result."
                )
            return "Target maturity level is met. Maintain the current process and its documentation."

        if evidence_status == "contradicted":
            return (
                "The uploaded evidence does not support the declared implementation. "
                "Review the implementation and update the supporting documentation before reassessing."
            )
        if evidence_status == "irrelevant":
            return (
                "The uploaded document does not address this control. Provide evidence that "
                "directly demonstrates the required implementation."
            )

        # Tailored recommendation via LLM (temperature 0).
        user_prompt = (
            f"CONTROL {control_number}: {control_title}\n"
            f"ASSESSED MATURITY: ML{maturity_level}\n"
            f"TARGET: ML{target}\n"
            f"EVIDENCE STATUS: {evidence_status or 'not provided'}\n"
            f"MISSING FOR NEXT LEVEL: {missing_for_next_level or 'not specified'}\n\n"
            "Write the recommendation now."
        )
        try:
            text = self._llm.complete(
                RECOMMENDATION_SYSTEM_PROMPT, user_prompt, max_tokens=300, temperature=0
            )
            return text.strip()
        except Exception as exc:  # noqa: BLE001
            # A recommendation is helpful but not critical — degrade gracefully
            # rather than failing the whole assessment if the LLM hiccups.
            logger.warning("Recommendation generation failed for %s: %s", control_number, exc)
            if missing_for_next_level:
                return f"To reach ML{min(maturity_level + 1, target)}: {missing_for_next_level}"
            return "Strengthen and document this control to progress toward the target maturity level."