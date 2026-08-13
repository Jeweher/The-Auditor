"""
File: app/application/services/maturity_engine.py
Folder: backend/app/application/services
Purpose: The Maturity Assessment Engine. It reproduces an auditor's
         reasoning rather than applying a fixed formula — but never lets the
         LLM decide freely.

         PIPELINE (see domain/maturity.py for the rules):
           1. Aggregate the control's answers + a single evidence_status.
           2. Deterministic rules compute a permitted band [min, max] given
              the declared target maturity level.
           3. If the band is fixed (e.g. all "no" -> ML0), return it WITHOUT
              calling the LLM — no cost, no drift.
           4. Otherwise the LLM, at temperature 0, picks a level inside the
              band and writes an auditor-style finding. Its choice is clamped
              to the band so it can never escape the rules.

         "Assessment", not "calculation": a TISAX auditor evaluates maturity
         by judgement against the VDA ISA definitions, not by arithmetic.
         Business rules bound the outcome; the LLM only exercises judgement
         where a human auditor would.
"""

import json
import logging
import re

from app.core.exceptions import ExternalServiceError
from app.domain.maturity import (
    MAX_MATURITY_LEVEL,
    Confidence,
    ControlAnswers,
    EvidenceStatus,
    compute_assessment_mode,
    compute_confidence,
    compute_maturity_band,
)
from app.domain.ports.llm_client import LLMPort

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> dict:
    cleaned = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ExternalServiceError("LLM returned malformed JSON.") from exc
    raise ExternalServiceError("LLM response contained no JSON object.")


MATURITY_DEFINITIONS = """Maturity levels (VDA ISA / based on ISO 15504 SPICE):
ML0 Incomplete — the process is not implemented or fails to achieve its purpose.
ML1 Performed — the process is carried out but informally, not or insufficiently documented; depends on individuals.
ML2 Managed — the process is documented, responsibilities are defined, and it is planned and tracked.
ML3 Established — a standard process is defined and consistently applied across the organisation.
ML4 Predictable — the process is measured with KPIs/metrics against defined performance thresholds.
ML5 Optimizing — the process is continuously improved through trend analysis and periodic optimisation."""

MATURITY_SYSTEM_PROMPT = f"""You are an experienced VDA ISA / TISAX assessor determining the maturity level of ONE control.

Use EXCLUSIVELY these definitions:
{MATURITY_DEFINITIONS}

You will be given the control, the user's answers, any evidence findings, and a PERMITTED RANGE [min, max]. You MUST choose an integer maturity level within that range — never outside it. The range encodes rules already established from the facts; respect it.

Compute the maturity level using this exact deterministic procedure — do not deviate, do not use outside judgement to override it:

1. Assign a weight to each answer: "yes" = 1, "partial" = 0.5, "no" = 0.
2. SPECIAL CASE: if there is at least one "no" AND there is no "yes" at all among the answers (only "no" and/or "partial"), the maturity level is 0. Stop here, do not compute further.
3. Otherwise, compute the average weight across all answered questions.
4. Multiply that average by the target maturity level given below.
5. Round to the nearest integer. If the result is exactly halfway between two integers (e.g. 1.5, 2.5), round to the nearest EVEN integer (1.5 -> 2, 2.5 -> 2, 0.5 -> 0, 3.5 -> 4).
6. Clamp the result to the permitted range given below — if your computed value falls outside it, use the nearest bound instead.

Do NOT show this calculation, any numbers, weights, or arithmetic in the finding. Never use the words "average", "weight", "formula", or similar. Write the finding exactly the way a professional auditor would in a real report: describe what was and wasn't demonstrated, in plain, natural prose — as if you had reasoned about it directly, not computed it.

Respond with ONLY a JSON object, no prose, no code fences:
{{
  "maturity_level": <integer within the permitted range>,
  "finding": "one or two sentences an auditor would write, explaining the level",
  "missing_for_next_level": "what would be required to reach the next level, or empty if at the top of the range"
}}"""


class MaturityAssessmentEngine:
    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def assess(
        self,
        control_number: str,
        control_question: str,
        requirements_text: str,
        responses: list[str],
        evidence_status: EvidenceStatus,
        target: int = 3,
        evidence_findings: str = "",
        qa_pairs: list[tuple[str, str]] | None = None,
    ) -> dict:
        answers = ControlAnswers(responses=responses, evidence_status=evidence_status)
        band = compute_maturity_band(answers, target)
        confidence = compute_confidence(answers)
        mode = compute_assessment_mode(evidence_status)

        # Fixed band -> rules decide, LLM not consulted.
        if band.is_fixed:
            return {
                "maturity_level": band.min_ml,
                "confidence": confidence.value,
                "assessment_mode": mode.value,
                "evidence_status": evidence_status.value,
                "finding": band.reason,
                "missing_for_next_level": "",
                "band_min": band.min_ml,
                "band_max": band.max_ml,
                "llm_used": False,
            }

        # Open band -> LLM picks within [min, max]. Prefer the paired
        # question+answer view — it lets the LLM judge how much of the
        # control's full scope was actually covered, not just tally yeses
        # with no idea what they were answers to.
        if qa_pairs:
            qa_lines = "\n".join(f"{i + 1}. {q} -> {a}" for i, (q, a) in enumerate(qa_pairs))
            answers_block = f"QUESTIONS AND ANSWERS:\n{qa_lines}"
        else:
            answers_block = f"USER ANSWERS: {', '.join(responses)}"

        user_prompt = (
            f"CONTROL {control_number}: {control_question}\n\n"
            f"REQUIREMENTS:\n{requirements_text}\n\n"
            f"{answers_block}\n\n"
            f"EVIDENCE FINDINGS: {evidence_findings or 'none provided'}\n\n"
            f"TARGET MATURITY LEVEL: {target}\n"
            f"PERMITTED RANGE: [{band.min_ml}, {band.max_ml}]\n"
            f"(Reason the range was set: {band.reason})\n\n"
            "Determine the maturity level now."
        )
        raw = self._llm.complete(
            MATURITY_SYSTEM_PROMPT, user_prompt, max_tokens=1000, temperature=0
        )
        parsed = _extract_json(raw)

        try:
            ml = int(parsed.get("maturity_level"))
        except (TypeError, ValueError) as exc:
            raise ExternalServiceError("LLM did not return a numeric maturity level.") from exc

        # Clamp to the permitted band AND to the absolute scale ceiling. The
        # LLM cannot escape the rules even if it tries.
        clamped = max(band.min_ml, min(band.max_ml, ml, MAX_MATURITY_LEVEL))
        if clamped != ml:
            logger.warning(
                "Control %s: LLM returned ML%d, clamped to ML%d (band [%d,%d])",
                control_number, ml, clamped, band.min_ml, band.max_ml,
            )

        return {
            "maturity_level": clamped,
            "confidence": confidence.value,
            "assessment_mode": mode.value,
            "evidence_status": evidence_status.value,
            "finding": str(parsed.get("finding", "")).strip(),
            "missing_for_next_level": str(parsed.get("missing_for_next_level", "")).strip(),
            "band_min": band.min_ml,
            "band_max": band.max_ml,
            "llm_used": True,
        }