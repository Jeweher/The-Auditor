"""
File: app/application/services/control_context_builder.py
Folder: backend/app/application/services
Purpose: Assembles the knowledge-base context for one control, filtered by
         the assessment's declared Assessment Level (AL).

         TISAX background: AL1/AL2/AL3 is the audit rigour the participant
         declares up front — it is an INPUT, not something derived from
         answers. It determines which requirement tiers apply:

             AL1 -> objective + must + should
             AL2 -> ... + "High protection:" section of `additional`
             AL3 -> ... + "Very high protection:" section too

         The `additional` chunk is one blob holding several tiers stacked
         ("High protection:", "Very high protection:", "SGA:"), so it must be
         split by marker before filtering — otherwise an AL2 participant
         would be asked AL3 questions.

         SGA (Simplified Group Assessment) is deliberately ignored: it is a
         multi-site audit sampling mode, orthogonal to AL — not a requirement
         tier. Including it under any AL would be a category error.
"""

import logging
import re

from app.core.exceptions import NotFoundError
from app.domain.ports.vector_store import VectorStorePort

logger = logging.getLogger(__name__)

VALID_ASSESSMENT_LEVELS = ("AL1", "AL2", "AL3")

# Which `additional` sections each AL unlocks. SGA is never included.
AL_SECTIONS = {
    "AL1": (),
    "AL2": ("High protection",),
    "AL3": ("High protection", "Very high protection"),
}

# Base chunk types always included, in reading order
BASE_SHEET_TYPES = ("objective", "must", "should")

SECTION_MARKER_RE = re.compile(
    r"^(High protection|Very high protection|SGA)\s*:\s*$", re.MULTILINE | re.IGNORECASE
)


def split_additional_sections(content: str) -> dict[str, str]:
    """Split an `additional` chunk into its protection tiers.

    The VDA ISA format stacks tiers with bare marker lines:
        High protection:
        + requirement...
        Very high protection:
        + requirement...
        SGA:
        + requirement...

    Returns {section_name: body}. Verified against all 33 `additional`
    chunks in the default corpus — every one matches at least one marker.
    """
    matches = list(SECTION_MARKER_RE.finditer(content))
    if not matches:
        return {}

    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start:end].strip()
        if body:
            # Normalise casing to the canonical form used in AL_SECTIONS
            canonical = name[0].upper() + name[1:].lower() if name.upper() != "SGA" else "SGA"
            if canonical.lower() == "very high protection":
                canonical = "Very high protection"
            elif canonical.lower() == "high protection":
                canonical = "High protection"
            sections[canonical] = body
    return sections


class ControlContextBuilder:
    def __init__(self, vector_store: VectorStorePort) -> None:
        self._vector_store = vector_store

    def build(self, collection: str, control_number: str, assessment_level: str) -> dict:
        """Fetch all chunks for one control and assemble the AL-filtered context.

        Returns {"control_question": str, "sections": [(label, text), ...]}.
        """
        if assessment_level not in VALID_ASSESSMENT_LEVELS:
            assessment_level = "AL1"

        docs = self._vector_store.get_documents(
            collection, where={"clause": control_number}, limit=50
        )
        if not docs:
            raise NotFoundError(f"No knowledge-base content found for control {control_number}.")

        by_type: dict[str, list[str]] = {}
        control_question = ""
        for doc in docs:
            sheet_type = str(doc.metadata.get("sheet_type", ""))
            if sheet_type == "control_parent":
                control_question = doc.content
                continue
            by_type.setdefault(sheet_type, []).append(doc.content)

        sections: list[tuple[str, str]] = []

        for sheet_type in BASE_SHEET_TYPES:
            for text in by_type.get(sheet_type, []):
                sections.append((sheet_type.capitalize(), text))

        allowed = AL_SECTIONS[assessment_level]
        if allowed:
            for text in by_type.get("additional", []):
                tiers = split_additional_sections(text)
                for tier_name in allowed:
                    if tier_name in tiers:
                        sections.append((tier_name, tiers[tier_name]))

        logger.info(
            "Built context for control %s at %s: %d sections",
            control_number,
            assessment_level,
            len(sections),
        )
        return {"control_question": control_question, "sections": sections}

    @staticmethod
    def to_prompt_text(context: dict) -> str:
        parts = []
        if context.get("control_question"):
            parts.append(f"CONTROL QUESTION:\n{context['control_question']}")
        for label, text in context.get("sections", []):
            parts.append(f"{label.upper()}:\n{text}")
        return "\n\n".join(parts)