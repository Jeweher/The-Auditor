"""
File: app/application/schemas/assessment.py
Folder: backend/app/application/schemas
Purpose: Request/response models for the assessment engine API (Phase 3).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --- Requests ---

class CreateAssessmentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    assessment_level: str = Field(
        default="AL1", description="AL1 | AL2 | AL3 — declared up front, filters which requirement tiers apply."
    )
    target_maturity_level: int = Field(
        default=3, ge=3, le=5, description="3 | 4 | 5 — target maturity. 4/5 require measurement evidence."
    )
    kb_collection: str | None = Field(
        default=None, description="Defaults to the default KB collection if omitted."
    )
    domain: str | None = Field(
        default=None, description="Optional: load controls from one domain only (IS, PP, DP)."
    )


class AnswerRequest(BaseModel):
    response: str | None = Field(
        default=None,
        description="yes | no | partial | skipped. Omit to let the LLM classify raw_text.",
    )
    raw_text: str | None = Field(default=None, description="Free-text answer, if any.")


class EditAnswerRequest(BaseModel):
    response: str | None = Field(
        default=None, description="yes | no | partial | skipped. Omit to re-classify raw_text."
    )
    raw_text: str | None = None


# --- Responses ---

class FollowupQuestionResponse(BaseModel):
    id: UUID
    question_text: str
    order_index: int
    evidence_expected: bool = False
    expected_documents: list[str] = []
    response: str | None = None
    raw_text: str | None = None
    llm_justification: str | None = None
    answer_id: UUID | None = None


class ControlResponse(BaseModel):
    id: UUID
    control_number: str
    domain: str
    title: str
    order_index: int
    state: str
    maturity_score: float | None = None


class ControlWithQuestionsResponse(ControlResponse):
    followup_questions: list[FollowupQuestionResponse] = []


class AssessmentResponse(BaseModel):
    id: UUID
    name: str
    kb_collection: str
    assessment_level: str
    target_maturity_level: int
    status: str

    created_at: datetime
    updated_at: datetime
    total_controls: int
    completed_controls: int
    skipped_controls: int
    progress_percent: float


class AnswerResponse(BaseModel):
    id: UUID
    followup_question_id: UUID
    response: str
    raw_text: str | None
    llm_justification: str | None = None
    answered_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    related_question_id: UUID | None = None
    related_answer_id: UUID | None = None
    created_at: datetime


class ResumeResponse(BaseModel):
    assessment: AssessmentResponse
    current_control: ControlWithQuestionsResponse | None
    message: str