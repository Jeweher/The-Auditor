"""
File: app/domain/maturity.py
Folder: backend/app/domain
Purpose: The deterministic core of maturity scoring. Pure functions, no I/O,
         no LLM — so every rule here is testable and reproducible.

         WHY THIS FILE EXISTS
         An LLM estimating "what maturity level is this control?" is a black
         box: it can drift, and a compliance tool that returns ML2 then ML3
         for identical inputs is indefensible. So the LLM never chooses
         freely. These rules compute a permitted band [min, max] from facts
         we know for certain (what the user answered, whether evidence was
         confirmed), and the LLM only picks within that band. Some cases are
         decided here outright and never reach the LLM at all.

         SCOPE: ML0-ML5. The VDA ISA target is normally 3, but the user may
         declare a higher target (4 or 5) to assess process maturity beyond
         the compliance minimum. ML4 (Predictable) and ML5 (Optimizing)
         require measurement/improvement EVIDENCE — they cannot be reached on
         a declaration alone. Without that evidence the result is capped at
         ML3, no matter what the user claims. This keeps the higher levels
         defensible: the engine never invents a KPI-based level from thin air.
"""

from dataclasses import dataclass
from enum import Enum

# Default VDA ISA target. The official Results sheet hardcodes 3, but the
# user can raise it per assessment.
DEFAULT_TARGET_MATURITY_LEVEL = 3
VALID_TARGET_LEVELS = (3, 4, 5)

# Absolute ceiling of the maturity scale.
MAX_MATURITY_LEVEL = 5

# A control can only reach ML4/ML5 with the corresponding evidence. Without
# it, this is the highest the engine will award.
CAP_WITHOUT_MEASUREMENT_EVIDENCE = 3


class EvidenceStatus(str, Enum):
    """State of the supporting document(s) for a control, as judged for the
    whole control (an auditor weighs all evidence together)."""

    NOT_REQUIRED = "not_required"  # no document would prove this control
    MISSING = "missing"  # a document was relevant but none was uploaded
    CONFIRMED = "confirmed"  # document(s) support the declaration
    PARTIALLY_CONFIRMED = "partially_confirmed"  # supported in part
    CONTRADICTED = "contradicted"  # document refutes the declaration
    IRRELEVANT = "irrelevant"  # document does not address this control
    # Higher-tier evidence, needed for ML4/ML5:
    MEASUREMENT_CONFIRMED = "measurement_confirmed"  # KPIs / metrics shown
    IMPROVEMENT_CONFIRMED = "improvement_confirmed"  # continuous improvement shown


class AssessmentMode(str, Enum):
    DECLARED = "declared"
    VERIFIED = "verified"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class MaturityBand:
    """The range the LLM is allowed to pick from, and why."""

    min_ml: int
    max_ml: int
    reason: str

    @property
    def is_fixed(self) -> bool:
        return self.min_ml == self.max_ml


@dataclass(frozen=True)
class ControlAnswers:
    """Aggregated answers for one control, as facts the rules can act on."""

    responses: list[str]  # "yes" | "no" | "partial" | "skipped"
    evidence_status: EvidenceStatus

    @property
    def answered(self) -> list[str]:
        return [r for r in self.responses if r != "skipped"]

    @property
    def all_no(self) -> bool:
        return bool(self.answered) and all(r == "no" for r in self.answered)

    @property
    def all_yes(self) -> bool:
        return bool(self.answered) and all(r == "yes" for r in self.answered)

    @property
    def any_no(self) -> bool:
        return any(r == "no" for r in self.answered)


def compute_maturity_band(answers: ControlAnswers, target: int = DEFAULT_TARGET_MATURITY_LEVEL) -> MaturityBand:
    """Bound what the LLM may decide, from facts alone.

    ML0 Incomplete — process absent or unsuitable
    ML1 Performed  — process happens but informal/undocumented
    ML2 Managed    — process documented, responsibilities defined
    ML3 Established— standard process, consistently applied
    ML4 Predictable— process measured with KPIs (requires measurement evidence)
    ML5 Optimizing — continuous improvement (requires improvement evidence)
    """
    if not answers.answered:
        return MaturityBand(0, 0, "No questions were answered for this control.")

    if answers.all_no:
        return MaturityBand(0, 0, "All requirements were answered 'no'.")

    if answers.evidence_status == EvidenceStatus.CONTRADICTED:
        return MaturityBand(0, 1, "Uploaded evidence contradicts the declared implementation.")

    if answers.any_no:
        return MaturityBand(0, 1, "At least one requirement is not implemented.")

    if not answers.all_yes:  # mixture of yes and partial
        return MaturityBand(1, 2, "Requirements are only partially implemented.")

    # From here: every answered question is "yes".
    # First establish the ML0-3 ceiling from process evidence.
    if answers.evidence_status == EvidenceStatus.IMPROVEMENT_CONFIRMED:
        # Continuous improvement demonstrated -> ML4/ML5 territory, capped by target.
        top = min(5, target)
        return MaturityBand(3, top, "All requirements implemented; continuous improvement evidence provided.")

    if answers.evidence_status == EvidenceStatus.MEASUREMENT_CONFIRMED:
        # Measurement/KPIs demonstrated -> up to ML4, capped by target.
        top = min(4, target)
        return MaturityBand(3, top, "All requirements implemented; measurement/KPI evidence provided.")

    if answers.evidence_status == EvidenceStatus.CONFIRMED:
        # Process confirmed but no measurement evidence -> ML3 ceiling.
        top = min(3, target)
        return MaturityBand(2, top, "All requirements declared implemented and evidence confirms it.")

    if answers.evidence_status == EvidenceStatus.PARTIALLY_CONFIRMED:
        return MaturityBand(1, min(3, target), "All requirements declared implemented; evidence supports them in part.")

    if answers.evidence_status == EvidenceStatus.IRRELEVANT:
        return MaturityBand(1, 2, "All requirements declared implemented, but the evidence provided does not address this control.")

    if answers.evidence_status == EvidenceStatus.NOT_REQUIRED:
        return MaturityBand(1, min(3, target), "All requirements declared implemented; no documentary evidence applies to this control.")

    # MISSING
    return MaturityBand(1, min(3, target), "All requirements declared implemented, but no supporting evidence was provided.")


def compute_confidence(answers: ControlAnswers) -> Confidence:
    """How reliable is the estimate — independent of how mature the control is.

    'no' scores HIGH: nothing to verify when someone states they do not do
    something. An unverified 'yes' is the least reliable case.
    """
    if answers.all_no:
        return Confidence.HIGH
    if answers.evidence_status in (
        EvidenceStatus.CONFIRMED,
        EvidenceStatus.CONTRADICTED,
        EvidenceStatus.MEASUREMENT_CONFIRMED,
        EvidenceStatus.IMPROVEMENT_CONFIRMED,
    ):
        return Confidence.HIGH
    if answers.evidence_status in (
        EvidenceStatus.PARTIALLY_CONFIRMED,
        EvidenceStatus.NOT_REQUIRED,
    ):
        return Confidence.MEDIUM
    if answers.evidence_status == EvidenceStatus.IRRELEVANT:
        return Confidence.LOW
    # MISSING
    return Confidence.LOW


def compute_assessment_mode(evidence_status: EvidenceStatus) -> AssessmentMode:
    """Verified only when a document was actually examined."""
    if evidence_status in (
        EvidenceStatus.CONFIRMED,
        EvidenceStatus.PARTIALLY_CONFIRMED,
        EvidenceStatus.CONTRADICTED,
        EvidenceStatus.IRRELEVANT,
        EvidenceStatus.MEASUREMENT_CONFIRMED,
        EvidenceStatus.IMPROVEMENT_CONFIRMED,
    ):
        return AssessmentMode.VERIFIED
    return AssessmentMode.DECLARED


def compute_completeness(
    total_questions: int, answered_questions: int, evidence_status: EvidenceStatus
) -> float:
    """How complete the information behind this control is (0-100). NOT a
    maturity score — a measure of how much we had to work with."""
    if total_questions == 0:
        return 0.0
    answer_ratio = answered_questions / total_questions
    if evidence_status == EvidenceStatus.MISSING:
        evidence_ratio = 0.0
    elif evidence_status == EvidenceStatus.NOT_REQUIRED:
        evidence_ratio = 1.0
    elif evidence_status == EvidenceStatus.PARTIALLY_CONFIRMED:
        evidence_ratio = 0.5
    elif evidence_status == EvidenceStatus.IRRELEVANT:
        evidence_ratio = 0.2
    else:  # CONFIRMED / CONTRADICTED / MEASUREMENT / IMPROVEMENT
        evidence_ratio = 1.0
    return round((answer_ratio * 0.7 + evidence_ratio * 0.3) * 100, 1)


def apply_cutback(maturity: float | None, target: int = DEFAULT_TARGET_MATURITY_LEVEL) -> float | None:
    """Cap the result at the declared target, mirroring the Results sheet:
        =IF(H23="na","",IF(H23="","",IF((H23)>G23,G23,(H23))))
    Exceeding the target earns nothing extra in TISAX scoring."""
    if maturity is None:
        return None
    return min(maturity, float(target))


def average_excluding_na(values: list[float | None]) -> float | None:
    """Mean over assessed controls only. Mirrors Excel COUNT semantics:
    skipped controls (None) drop out of numerator AND denominator rather
    than counting as zero."""
    assessed = [v for v in values if v is not None]
    if not assessed:
        return None
    return round(sum(assessed) / len(assessed), 2)