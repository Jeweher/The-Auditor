"""
File: app/application/services/evidence_services.py
Folder: backend/app/application/services
Purpose: The two evidence-related LLM capabilities, mirroring what a TISAX
         auditor does: first decide whether a document is even relevant for a
         given requirement, then — if one is supplied — judge how well it
         backs the declaration.

         EvidenceRequirementDetector: reads a follow-up question + the
         control's requirements and answers "would a document prove this?".
         Practices describable orally (e.g. "responsibilities are assigned")
         need none; anything resting on a policy, procedure, log, record or
         report does.

         EvidenceAnalyzerService: given the extracted text of an uploaded
         file, returns a verdict (confirmed / partially / contradicted /
         irrelevant / measurement_confirmed / improvement_confirmed), a
         relevance score, and which requirement tiers it covers. The two
         measurement verdicts are what unlock ML4/ML5 upstream. Runs at
         temperature 0 for reproducibility.
"""

import json
import logging
import re

from app.core.exceptions import ExternalServiceError
from app.domain.ports.llm_client import LLMPort

logger = logging.getLogger(__name__)

VALID_VERDICTS = (
    "confirmed",
    "partially_confirmed",
    "contradicted",
    "irrelevant",
    "measurement_confirmed",
    "improvement_confirmed",
)


def _extract_json(text: str) -> dict | list:
    cleaned = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r"[\[{].*[\]}]", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ExternalServiceError("LLM returned malformed JSON.") from exc
    raise ExternalServiceError("LLM response contained no JSON.")


EVIDENCE_NEEDED_SYSTEM_PROMPT = """You are a VDA ISA / TISAX assessor deciding whether documentary evidence is relevant for a specific assessment question.

A document is relevant when the requirement rests on something written or recorded: a policy, procedure, guideline, register, log, report, record, certificate, screenshot of a configured system, training record, or similar.

A document is NOT relevant when the requirement is an organisational practice that an auditor would confirm by interview or observation, not by reading a file.

Respond with ONLY a JSON object, no prose, no code fences:
{"evidence_expected": true|false, "expected_documents": ["short label", ...]}
If evidence_expected is false, expected_documents is an empty list."""


EVIDENCE_ANALYSIS_SYSTEM_PROMPT = """You are an experienced VDA ISA / TISAX assessor examining a document an organisation submitted as evidence for a control.

You are given: the control's question, its requirements, the user's declared answers, the target maturity level, and the extracted text of the uploaded document.

Judge the document exactly as an auditor would:
- Is it relevant to THIS control, or unrelated?
- Does it substantiate what the user declared?
- Which requirements does it cover, and which does it leave unaddressed?
- Does anything contradict the declaration (a draft, an expired date, a scope that excludes the requirement)?
- Does it show PROCESS MEASUREMENT (KPIs, metrics, defined thresholds, statistics)? This matters only if the target is 4 or higher.
- Does it show CONTINUOUS IMPROVEMENT (trend analysis, periodic reviews leading to documented optimisation)? This matters only if the target is 5.

Choose ONE verdict:
- "confirmed" — supports the declared implementation (process established)
- "partially_confirmed" — supports some requirements, leaves gaps
- "contradicted" — refutes the declaration
- "irrelevant" — does not address this control
- "measurement_confirmed" — confirms the process AND shows KPI/measurement evidence (only if target >= 4)
- "improvement_confirmed" — confirms measurement AND continuous improvement (only if target = 5)

Respond with ONLY a JSON object, no prose, no code fences:
{
  "verdict": "confirmed|partially_confirmed|contradicted|irrelevant|measurement_confirmed|improvement_confirmed",
  "relevance": 0-100,
  "coverage": {"must": "covered|partial|missing", "should": "covered|partial|missing|na", "protection": "covered|partial|missing|na"},
  "summary": "one or two sentences an auditor would write",
  "missing_elements": ["short label", ...]
}"""


class EvidenceRequirementDetector:
    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def is_evidence_expected(self, question_text: str, requirements_text: str) -> tuple[bool, list[str]]:
        user_prompt = (
            f"QUESTION:\n{question_text}\n\n"
            f"CONTROL REQUIREMENTS:\n{requirements_text}\n\n"
            "Is documentary evidence relevant for this question?"
        )
        raw = self._llm.complete(
            EVIDENCE_NEEDED_SYSTEM_PROMPT, user_prompt, max_tokens=500, temperature=0
        )
        parsed = _extract_json(raw)
        if not isinstance(parsed, dict):
            raise ExternalServiceError("LLM did not return an evidence decision object.")
        expected = bool(parsed.get("evidence_expected", False))
        docs = parsed.get("expected_documents", []) or []
        docs = [str(d).strip() for d in docs if str(d).strip()]
        return expected, docs


class EvidenceAnalyzerService:
    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def analyze(
        self,
        control_question: str,
        requirements_text: str,
        declared_answers: str,
        evidence_text: str,
        target_maturity: int = 3,
    ) -> dict:
        user_prompt = (
            f"CONTROL QUESTION:\n{control_question}\n\n"
            f"REQUIREMENTS:\n{requirements_text}\n\n"
            f"USER DECLARED:\n{declared_answers}\n\n"
            f"TARGET MATURITY LEVEL: {target_maturity}\n\n"
            f"UPLOADED DOCUMENT (extracted text):\n{evidence_text}\n\n"
            "Assess this document now."
        )
        raw = self._llm.complete(
            EVIDENCE_ANALYSIS_SYSTEM_PROMPT, user_prompt, max_tokens=1200, temperature=0
        )
        parsed = _extract_json(raw)
        if not isinstance(parsed, dict):
            raise ExternalServiceError("LLM did not return an analysis object.")

        verdict = str(parsed.get("verdict", "")).strip().lower()
        if verdict not in VALID_VERDICTS:
            raise ExternalServiceError(f"LLM returned an invalid verdict: {verdict!r}.")

        try:
            relevance = int(parsed.get("relevance", 0))
        except (TypeError, ValueError):
            relevance = 0
        relevance = max(0, min(100, relevance))

        coverage = parsed.get("coverage", {})
        if not isinstance(coverage, dict):
            coverage = {}

        summary = str(parsed.get("summary", "")).strip()
        missing = parsed.get("missing_elements", []) or []
        missing = [str(m).strip() for m in missing if str(m).strip()]

        return {
            "verdict": verdict,
            "relevance": relevance,
            "coverage": coverage,
            "summary": summary,
            "missing_elements": missing,
        }