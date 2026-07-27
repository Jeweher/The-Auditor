"""
File: app/application/schemas/report.py
Folder: backend/app/application/schemas
Purpose: Response models for evidence, control assessment, and the report /
         dashboard endpoints (Phase 5+6).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# --- Evidence ---

class EvidenceAnalysisResponse(BaseModel):
    verdict: str
    relevance: int
    coverage: dict | None = None
    summary: str | None = None
    missing_elements: list[str] = []


class EvidenceResponse(BaseModel):
    id: UUID
    answer_id: UUID
    filename: str
    file_type: str
    size: int
    created_at: datetime
    analysis: EvidenceAnalysisResponse | None = None


# --- Control assessment ---

class AssessControlResponse(BaseModel):
    control_id: UUID
    control_number: str
    maturity_level: int
    confidence: str
    assessment_mode: str
    evidence_status: str
    finding: str
    missing_for_next_level: str
    recommendation: str
    band_min: int
    band_max: int
    llm_used: bool


# --- Report ---

class ReportSummary(BaseModel):
    overall_maturity: float | None
    compliance_percent: float
    total_controls: int
    assessed_controls: int
    skipped_controls: int
    controls_at_target: int
    controls_below_target: int
    assessment_completeness: float
    verified_controls: int
    declared_controls: int
    verified_percent: float
    declared_percent: float


class AggregateRow(BaseModel):
    key: str
    average_maturity: float | None
    target: int
    gap: float | None
    assessed_controls: int


class ControlRow(BaseModel):
    control_number: str
    domain: str
    title: str
    state: str
    maturity_level: float | None
    cutback_level: float | None
    target_level: int | None
    gap: float | None
    confidence: str | None
    assessment_mode: str | None
    evidence_status: str | None
    finding: str | None
    recommendation: str | None
    missing_for_next_level: str | None


class ReportResponse(BaseModel):
    assessment_id: str
    name: str
    assessment_level: str
    target_maturity_level: int
    status: str
    summary: ReportSummary
    maturity_distribution: dict
    confidence_distribution: dict
    evidence_distribution: dict
    by_domain: list[AggregateRow]
    by_subchapter: list[AggregateRow]
    controls: list[ControlRow]