"""
File: app/application/services/llm_services.py
Folder: backend/app/application/services
Purpose: The two LLM-backed capabilities of Phase 4:

         1. QuestionGeneratorService — reads a control's requirements
            (AL-filtered) and extracts 1-3 grouped follow-up questions.
         2. AnswerClassifierService — turns a free-text answer into a
            structured yes/no/partial verdict with a justification.

         Both depend only on LLMPort, so the provider stays swappable.
         Both parse strict JSON from the model and fail loudly rather than
         guessing when the response is malformed.
"""

import json
import logging
import re

from app.core.exceptions import ExternalServiceError
from app.domain.ports.llm_client import LLMPort

logger = logging.getLogger(__name__)

# Question budget per Assessment Level. AL3 gets one extra because it
# unlocks two protection tiers on top of must/should, and squeezing four
# tiers into three questions forced the model to drop the very-high tier
# entirely — observed on control 1.6.2 during Phase 4 testing.
MAX_QUESTIONS_BY_AL = {"AL1": 3, "AL2": 3, "AL3": 4}
MAX_QUESTIONS = 4  # hard ceiling, any AL
VALID_RESPONSES = ("yes", "no", "partial")


def _extract_json(text: str) -> dict | list:
    """Models sometimes wrap JSON in prose or code fences despite instructions.
    Strip fences, then take the outermost JSON value."""
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


def _build_question_system_prompt(max_questions: int, section_labels: list[str]) -> str:
    """The prompt depends on the control at hand: how many questions are
    allowed, and which requirement tiers the AL actually unlocked."""
    tiers = ", ".join(section_labels) if section_labels else "the sections provided"
    return f"""You are a TISAX (VDA ISA) compliance assessor conducting a guided self-assessment interview.

The requirements below are grouped into labelled sections: {tiers}. Each section is a distinct requirement tier and must be assessed on its own terms.

Produce between 1 and {max_questions} follow-up questions.

Rules:
- Maximum {max_questions} questions. Never more.
- NEVER mix two different sections into one question. A question covers one section only.
- WITHIN a section, group related requirements into a single question rather than asking them one by one. Several bullet points sharing an idea belong in one well-phrased question.
- EVERY section provided must be covered by at least one question. Do not drop a section because you ran out of room — compress within sections instead.
- If a section is rich enough to need more than one question and the budget allows, split it.
- Each question must be answerable with yes / no / partially.
- Ask about what the organisation actually does — not about the standard's wording.
- Be concise and concrete. No preamble, no numbering inside the text.
- Write the questions in the same language as the requirements provided.

Respond with ONLY a JSON array of strings, ordered by section as given. No prose, no code fences.
Example: ["Question one?", "Question two?"]"""


CLASSIFIER_SYSTEM_PROMPT_YES_NO = """You are a TISAX compliance assessor interpreting a free-text answer.

Given an assessment question and the respondent's answer in their own words, classify it as either "yes" or "no". This assessment does not use a "partial" category — even if the answer sounds partially met, choose whichever of "yes" or "no" is the more honest characterization, and note any nuance in the justification.

Classification:
- "yes" — the requirement is met, even if imperfectly implemented. A brief, unqualified affirmative ("yes", "sure", "correct", "we do", "absolutely") counts as "yes".
- "no" — not met, absent, the respondent says they don't do it, or the gap described is significant enough that it cannot honestly be called met.

Respond with ONLY a JSON object, no prose, no code fences:
{"response": "yes|no", "justification": "one short sentence explaining the classification, noting any nuance"}"""


CLASSIFIER_SYSTEM_PROMPT = """You are a TISAX compliance assessor interpreting a free-text answer.

Given an assessment question and the respondent's answer in their own words, classify how well the answer satisfies the question.

Classification:
- "yes" — the requirement is fully met. A brief, unqualified affirmative ("yes", "sure", "correct", "we do", "absolutely") counts as "yes" — do not downgrade it to "partial" just because it is short.
- "partial" — the answer itself signals a limitation: partially met, in progress, informal, outdated, "mostly", "sometimes", or notable gaps described by the respondent.
- "no" — not met, absent, or the respondent says they don't do it. A brief, unqualified negative ("no", "not really", "we don't") counts as "no".

Only classify as "partial" when the respondent's own words indicate a limitation — never infer a limitation the respondent did not state.

Respond with ONLY a JSON object, no prose, no code fences:
{"response": "yes|no|partial", "justification": "one short sentence explaining the classification"}"""


class QuestionGeneratorService:
    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def generate(
        self,
        control_number: str,
        context_text: str,
        assessment_level: str = "AL1",
        section_labels: list[str] | None = None,
    ) -> list[str]:
        budget = MAX_QUESTIONS_BY_AL.get(assessment_level, 3)
        system_prompt = _build_question_system_prompt(budget, section_labels or [])
        user_prompt = (
            f"Control {control_number}\n\n"
            f"{context_text}\n\n"
            f"Produce the follow-up questions now."
        )
        raw = self._llm.complete(system_prompt, user_prompt, max_tokens=1500)
        parsed = _extract_json(raw)

        if not isinstance(parsed, list):
            raise ExternalServiceError("LLM did not return a list of questions.")

        questions = [str(q).strip() for q in parsed if str(q).strip()]
        if not questions:
            raise ExternalServiceError("LLM returned no usable questions.")

        if len(questions) > budget:
            logger.warning(
                "LLM returned %d questions for control %s at %s; truncating to %d",
                len(questions),
                control_number,
                assessment_level,
                budget,
            )
            questions = questions[:budget]
        return questions


class AnswerClassifierService:
    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def classify(
        self, question_text: str, raw_text: str, response_scale: str = "yes_no_partial"
    ) -> tuple[str, str]:
        """Returns (response, justification)."""
        if response_scale == "yes_no":
            system_prompt = CLASSIFIER_SYSTEM_PROMPT_YES_NO
            allowed = ("yes", "no")
        else:
            system_prompt = CLASSIFIER_SYSTEM_PROMPT
            allowed = VALID_RESPONSES

        user_prompt = f"QUESTION:\n{question_text}\n\nANSWER:\n{raw_text}"
        raw = self._llm.complete(system_prompt, user_prompt, max_tokens=1000, temperature=0)
        parsed = _extract_json(raw)

        if not isinstance(parsed, dict):
            raise ExternalServiceError("LLM did not return a classification object.")

        response = str(parsed.get("response", "")).strip().lower()
        if response not in allowed:
            raise ExternalServiceError(
                f"LLM returned an invalid classification: {response!r}."
            )
        justification = str(parsed.get("justification", "")).strip()
        return response, justification