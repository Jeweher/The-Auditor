"""
File: app/api/v1/routers/assessment.py
Folder: backend/app/api/v1/routers
Purpose: HTTP layer for the assessment engine (Phase 3). All routes require
         auth. Routes stay thin: parse input, call AssessmentService, shape
         the response. Domain exceptions are handled globally.
"""

import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import StreamingResponse
import io
from app.api.v1.deps import get_assessment_service, get_current_user
from app.application.schemas.assessment import (
    AnswerRequest,
    AnswerResponse,
    AssessmentResponse,
    ControlWithQuestionsResponse,
    CreateAssessmentRequest,
    EditAnswerRequest,
    FollowupQuestionResponse,
    MessageResponse,
    ResumeResponse,
)
from app.application.schemas.report import (
    AssessControlResponse,
    EvidenceAnalysisResponse,
    EvidenceResponse,
    ReportResponse,
)
from app.application.services.assessment_service import AssessmentService
from app.domain.entities.user import User

router = APIRouter(prefix="/api/v1/assessments", tags=["assessments"])


def _assessment_to_response(service: AssessmentService, assessment) -> AssessmentResponse:
    progress = service.get_progress(assessment)
    return AssessmentResponse(
        id=assessment.id,
        name=assessment.name,
        kb_collection=assessment.kb_collection,
        assessment_level=assessment.assessment_level,
        target_maturity_level=assessment.target_maturity_level,
        evidence_mode=assessment.evidence_mode,
        response_scale=assessment.response_scale,
        sample_percent=assessment.sample_percent,
        kb_source_filename=assessment.kb_source_filename,
        status=assessment.status,
        
        
        created_at=assessment.created_at,
        updated_at=assessment.updated_at,
        **progress,
    )


def _control_to_response(control) -> ControlWithQuestionsResponse:
    questions = []
    for q in sorted(control.followup_questions, key=lambda x: x.order_index):
        ans = q.answer
        evidence_item = ans.evidence[0] if ans and ans.evidence else None
        questions.append(
            FollowupQuestionResponse(
                id=q.id,
                question_text=q.question_text,
                order_index=q.order_index,
                evidence_expected=q.evidence_expected,
                expected_documents=json.loads(q.expected_documents) if q.expected_documents else [],
                response=ans.response if ans else None,
                raw_text=ans.raw_text if ans else None,
                llm_justification=ans.llm_justification if ans else None,
                answer_id=ans.id if ans else None,
                evidence_id=evidence_item.id if evidence_item else None,
                evidence_filename=evidence_item.filename if evidence_item else None,
            )
        )
    return ControlWithQuestionsResponse(
        id=control.id,
        control_number=control.control_number,
        domain=control.domain,
        title=control.title,
        order_index=control.order_index,
        state=control.state,
        maturity_score=control.maturity_score,
        followup_questions=questions,
    )


@router.post("", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
def create_assessment(
    payload: CreateAssessmentRequest,
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> AssessmentResponse:
    assessment = service.create_assessment(
        user_id=user.id,
        name=payload.name,
        kb_collection=payload.kb_collection,
        domain=payload.domain,
        assessment_level=payload.assessment_level,
        target_maturity_level=payload.target_maturity_level,
        evidence_mode=payload.evidence_mode,
        response_scale=payload.response_scale,
        sample_percent=payload.sample_percent,
        kb_source_filename=payload.kb_source_filename,
    )
    return _assessment_to_response(service, assessment)


@router.get("", response_model=list[AssessmentResponse])
def list_assessments(
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[AssessmentResponse]:
    return [_assessment_to_response(service, a) for a in service.list_assessments(user.id)]


@router.get("/{assessment_id}", response_model=AssessmentResponse)
def get_assessment(
    assessment_id: UUID,
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> AssessmentResponse:
    assessment = service._get_owned_assessment(assessment_id, user.id)
    return _assessment_to_response(service, assessment)


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assessment(
    assessment_id: UUID,
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    service.delete_assessment(assessment_id, user.id)


@router.get("/{assessment_id}/current", response_model=ControlWithQuestionsResponse | None)
def get_current_control(
    assessment_id: UUID,
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> ControlWithQuestionsResponse | None:
    control = service.get_current_control(assessment_id, user.id)
    return _control_to_response(control) if control else None
@router.get("/{assessment_id}/controls", response_model=list[ControlWithQuestionsResponse])
def list_controls(
    assessment_id: UUID,
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[ControlWithQuestionsResponse]:
    controls = service.list_controls(assessment_id, user.id)
    return [_control_to_response(c) for c in controls]


@router.post("/controls/{control_id}/start", response_model=ControlWithQuestionsResponse)
def start_control(
    control_id: UUID,
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> ControlWithQuestionsResponse:
    control = service.start_control(control_id, user.id)
    return _control_to_response(control)


@router.post("/controls/{control_id}/skip", response_model=ControlWithQuestionsResponse)
def skip_control(
    control_id: UUID,
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> ControlWithQuestionsResponse:
    control = service.skip_control(control_id, user.id)
    return _control_to_response(control)


@router.post("/questions/{question_id}/answer", response_model=AnswerResponse, status_code=status.HTTP_201_CREATED)
def answer_question(
    question_id: UUID,
    payload: AnswerRequest,
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> AnswerResponse:
    answer = service.answer_question(question_id, user.id, payload.response, payload.raw_text)
    return AnswerResponse(
        id=answer.id,
        followup_question_id=answer.followup_question_id,

        response=answer.response,
        raw_text=answer.raw_text,
        llm_justification=answer.llm_justification,
        answered_at=answer.answered_at,
        updated_at=answer.updated_at,
    
    )


@router.patch("/answers/{answer_id}", response_model=AnswerResponse)
def edit_answer(
    answer_id: UUID,
    payload: EditAnswerRequest,
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> AnswerResponse:
    answer = service.edit_answer(answer_id, user.id, payload.response, payload.raw_text)
    return AnswerResponse(
        id=answer.id,
        followup_question_id=answer.followup_question_id,

        response=answer.response,
        raw_text=answer.raw_text,
        llm_justification=answer.llm_justification,
        answered_at=answer.answered_at,
        updated_at=answer.updated_at,
    
    )


@router.get("/{assessment_id}/resume", response_model=ResumeResponse)
def resume_assessment(
    assessment_id: UUID,
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> ResumeResponse:
    assessment = service._get_owned_assessment(assessment_id, user.id)
    current = service.get_current_control(assessment_id, user.id)
    if current is None:
        msg = "All controls have been answered or skipped. Assessment is complete."
    else:
        msg = f"Resuming at control {current.control_number}."
    return ResumeResponse(
        assessment=_assessment_to_response(service, assessment),
        current_control=_control_to_response(current) if current else None,
        message=msg,
    )


@router.get("/{assessment_id}/messages", response_model=list[MessageResponse])
def get_messages(
    assessment_id: UUID,
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[MessageResponse]:
    messages = service.get_messages(assessment_id, user.id)
    return [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            related_question_id=m.related_question_id,
            related_answer_id=m.related_answer_id,
            created_at=m.created_at,
        )
        for m in messages
    ]
# ─────────────────────────────────────────────────────────────────────
# Phase 5 — Evidence
# ─────────────────────────────────────────────────────────────────────

def _evidence_to_response(evidence) -> EvidenceResponse:
    analysis = None
    if evidence.analysis is not None:
        a = evidence.analysis
        analysis = EvidenceAnalysisResponse(
            verdict=a.verdict,
            relevance=a.relevance,
            coverage=json.loads(a.coverage) if a.coverage else None,
            summary=a.summary,
            missing_elements=json.loads(a.missing_elements) if a.missing_elements else [],
        )
    return EvidenceResponse(
        id=evidence.id,
        answer_id=evidence.answer_id,
        filename=evidence.filename,
        file_type=evidence.file_type,
        size=evidence.size,
        created_at=evidence.created_at,
        analysis=analysis,
    )


@router.post(
    "/answers/{answer_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_evidence(
    answer_id: UUID,
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> EvidenceResponse:
    content = await file.read()
    evidence = service.upload_evidence(
        answer_id=answer_id,
        user_id=user.id,
        filename=file.filename or "evidence",
        file_type=file.content_type or "application/octet-stream",
        content=content,
    )
    return _evidence_to_response(evidence)


@router.post("/evidence/{evidence_id}/analyze", response_model=EvidenceResponse)
def analyze_evidence(
    evidence_id: UUID,
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> EvidenceResponse:
    evidence = service.analyze_evidence(evidence_id, user.id)
    return _evidence_to_response(evidence)

@router.get("/evidence/{evidence_id}/download")
def download_evidence(
    evidence_id: UUID,
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
):
    content, evidence = service.get_evidence_file(evidence_id, user.id)
    return StreamingResponse(
        io.BytesIO(content),
        media_type=evidence.file_type,
        headers={"Content-Disposition": f'inline; filename="{evidence.filename}"'},
    )


# ─────────────────────────────────────────────────────────────────────
# Phase 6 — Maturity assessment + report
# ─────────────────────────────────────────────────────────────────────

@router.post("/controls/{control_id}/assess", response_model=AssessControlResponse)
def assess_control(
    control_id: UUID,
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> AssessControlResponse:
    control = service.assess_control(control_id, user.id)
    return AssessControlResponse(
        control_id=control.id,
        control_number=control.control_number,
        maturity_level=int(control.maturity_score),
        confidence=control.confidence or "",
        assessment_mode=control.assessment_mode or "",
        evidence_status=control.evidence_status or "",
        finding=control.finding or "",
        missing_for_next_level=control.missing_for_next_level or "",
        recommendation=control.recommendation or "",
        band_min=0,
        band_max=5,
        llm_used=True,
    )
# ── Report (Phase 6) ──────────────────────────────────────────────

def build_report(self, assessment_id: UUID, user_id: UUID) -> dict:
        """Assemble the full report + dashboard figures from persisted control
        results. Pure aggregation, no LLM — reproducible on every call."""
        from app.application.services.report_service import ReportService

        assessment = self._get_owned_assessment(assessment_id, user_id)
        controls = self._controls_ordered(assessment_id)
        report_service = ReportService(target=assessment.target_maturity_level)
        return report_service.build_report(assessment, controls)


@router.get("/{assessment_id}/report", response_model=ReportResponse)
def get_report(
    assessment_id: UUID,
    service: Annotated[AssessmentService, Depends(get_assessment_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> ReportResponse:
    report = service.build_report(assessment_id, user.id)
    return ReportResponse(**report)

