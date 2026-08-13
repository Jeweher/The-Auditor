"""
File: app/application/services/assessment_service.py
Folder: backend/app/application/services
Purpose: Core business logic for the assessment engine. Handles: creating an
         assessment (auto-loading its controls in order from the KB, at a
         declared Assessment Level), the per-control state machine, answering
         + editing answers, skipping, conversation-message logging (the
         "ChatGPT-like memory"), and resume.

         Phase 4 wired the LLM in at exactly two points, both optional —
         if no LLM is supplied the service still runs with placeholders and
         literal responses, which keeps Phase 3's tests valid:
           - _generate_followup_questions(): real questions from the control's
             AL-filtered requirements
           - answer_question()/edit_answer(): free-text -> yes/no/partial
"""

import logging
import random
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

import hashlib
import json

from app.application.services.control_context_builder import (
    VALID_ASSESSMENT_LEVELS,
    ControlContextBuilder,
)
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.maturity import EvidenceStatus, VALID_TARGET_LEVELS, apply_cutback
from app.infrastructure.db.models import (
    AnswerModel,
    AssessmentControlModel,
    AssessmentModel,
    ConversationMessageModel,
    EvidenceAnalysisModel,
    EvidenceModel,
    FollowupQuestionModel,
)
from app.infrastructure.evidence.text_extractor import extract_text

logger = logging.getLogger(__name__)

VALID_RESPONSES = {"yes", "no", "partial", "skipped"}
PLACEHOLDER_QUESTION_COUNT = 3


class AssessmentService:
    def __init__(
        self,
        db: Session,
        query_service,
        context_builder: ControlContextBuilder | None = None,
        question_generator=None,
        answer_classifier=None,
        evidence_detector=None,
        evidence_analyzer=None,
        maturity_engine=None,
        recommendation_service=None,
        file_storage=None,
    ) -> None:
        # query_service: KnowledgeBaseQueryService, used to load controls from the KB.
        # LLM/storage collaborators are optional: when absent the service falls
        # back to earlier behaviour, which keeps it testable without an API key.
        self._db = db
        self._kb = query_service
        self._context_builder = context_builder
        self._question_generator = question_generator
        self._answer_classifier = answer_classifier
        self._evidence_detector = evidence_detector
        self._evidence_analyzer = evidence_analyzer
        self._maturity_engine = maturity_engine
        self._recommendation = recommendation_service
        self._storage = file_storage

    # ── Creation ──────────────────────────────────────────────────────

    def create_assessment(
        self,
        user_id: UUID,
        name: str,
        kb_collection: str | None,
        domain: str | None,
        assessment_level: str = "AL1",
        target_maturity_level: int = 3,
        evidence_mode: str = "with_evidence",
        response_scale: str = "yes_no_partial",
        sample_percent: int | None = None,
        kb_source_filename: str | None = None,
    ) -> AssessmentModel:
        if assessment_level not in VALID_ASSESSMENT_LEVELS:
            raise ValidationError(
                f"assessment_level must be one of {list(VALID_ASSESSMENT_LEVELS)}."
            )
        if target_maturity_level not in VALID_TARGET_LEVELS:
            raise ValidationError(
                f"target_maturity_level must be one of {list(VALID_TARGET_LEVELS)}."
            )

        valid_evidence_modes = ("with_evidence", "no_evidence")
        if evidence_mode not in valid_evidence_modes:
            raise ValidationError(f"evidence_mode must be one of {list(valid_evidence_modes)}.")

        valid_response_scales = ("yes_no_partial", "yes_no")
        if response_scale not in valid_response_scales:
            raise ValidationError(f"response_scale must be one of {list(valid_response_scales)}.")

        valid_sample_percents = (10, 20, 30, 40, 50, 60, 70, 80, 90)
        if sample_percent is not None and sample_percent not in valid_sample_percents:
            raise ValidationError(
                f"sample_percent must be one of {list(valid_sample_percents)}, or omitted for 100%."
            )

        collection = self._kb._resolve_collection(kb_collection)  # validates existence
        controls = self._kb.list_controls(collection, domain)
        if not controls:
            raise ValidationError("No controls found in the selected knowledge base.")

        # Random sampling: pick WHICH controls are included, but keep them in
        # their normal catalogue order for the interview — only the subset
        # changes, not the sequencing.
        if sample_percent is not None:
            sample_size = max(1, round(len(controls) * sample_percent / 100))
            sampled_indices = sorted(random.sample(range(len(controls)), k=sample_size))
            controls = [controls[i] for i in sampled_indices]

        assessment = AssessmentModel(
            user_id=user_id,
            name=name,
            kb_collection=collection,
            assessment_level=assessment_level,
            target_maturity_level=target_maturity_level,
            evidence_mode=evidence_mode,
            response_scale=response_scale,
            sample_percent=sample_percent,
            kb_source_filename=kb_source_filename,
        )

        self._db.add(assessment)
        self._db.flush()  # get assessment.id

        for idx, c in enumerate(controls):
            self._db.add(
                AssessmentControlModel(
                    assessment_id=assessment.id,
                    control_number=c["control_number"],
                    domain=c["domain"],
                    title=c["title"],
                    order_index=idx,
                    state="not_started",
                )
            )

        # Opening bot message (ChatGPT-like memory starts here)
        self._db.add(
            ConversationMessageModel(
                assessment_id=assessment.id,
                role="bot",
                content=(
                    f"Assessment '{name}' started at {assessment_level}, target ML{target_maturity_level}. "
                    f"It contains {len(controls)} controls. Let's begin with the first one."
                ),
            )
        )
        self._db.commit()
        self._db.refresh(assessment)
        logger.info("Created assessment %s with %d controls", assessment.id, len(controls))
        return assessment

    # ── Retrieval / progress ──────────────────────────────────────────

    def _get_owned_assessment(self, assessment_id: UUID, user_id: UUID) -> AssessmentModel:
        assessment = self._db.get(AssessmentModel, assessment_id)
        if assessment is None or assessment.user_id != user_id:
            raise NotFoundError("Assessment not found.")
        return assessment

    def list_assessments(self, user_id: UUID) -> list[AssessmentModel]:
        stmt = (
            select(AssessmentModel)
            .where(AssessmentModel.user_id == user_id)
            .order_by(AssessmentModel.created_at.desc())
        )
        return list(self._db.execute(stmt).scalars().all())

    def get_progress(self, assessment: AssessmentModel) -> dict:
        controls = assessment.controls
        total = len(controls)
        completed = sum(1 for c in controls if c.state in ("answered", "completed"))
        skipped = sum(1 for c in controls if c.state == "skipped")
        done = completed + skipped
        progress = round((done / total) * 100, 1) if total else 0.0
        return {
            "total_controls": total,
            "completed_controls": completed,
            "skipped_controls": skipped,
            "progress_percent": progress,
        }

    def delete_assessment(self, assessment_id: UUID, user_id: UUID) -> None:
        assessment = self._get_owned_assessment(assessment_id, user_id)
        self._db.delete(assessment)
        self._db.commit()

    # ── Cursor / current control ──────────────────────────────────────

    def _controls_ordered(self, assessment_id: UUID) -> list[AssessmentControlModel]:
        stmt = (
            select(AssessmentControlModel)
            .where(AssessmentControlModel.assessment_id == assessment_id)
            .order_by(AssessmentControlModel.order_index)
            .options(selectinload(AssessmentControlModel.followup_questions).selectinload(
                FollowupQuestionModel.answer
            ))
        )
        return list(self._db.execute(stmt).scalars().all())
    def list_controls(self, assessment_id: UUID, user_id: UUID) -> list[AssessmentControlModel]:
        self._get_owned_assessment(assessment_id, user_id)
        return self._controls_ordered(assessment_id)

    def get_current_control(self, assessment_id: UUID, user_id: UUID) -> AssessmentControlModel | None:
        """First control not yet completed or skipped = where the cursor is."""
        self._get_owned_assessment(assessment_id, user_id)
        for control in self._controls_ordered(assessment_id):
            if control.state not in ("completed", "skipped", "answered"):
                return control
        return None

    def _get_owned_control(self, control_id: UUID, user_id: UUID) -> AssessmentControlModel:
        control = self._db.get(AssessmentControlModel, control_id)
        if control is None:
            raise NotFoundError("Control not found.")
        self._get_owned_assessment(control.assessment_id, user_id)
        return control

    # ── Start a control: generate followup questions ──────────────────
    def _control_requirements_text(self, control: AssessmentControlModel) -> str:
        """The AL-filtered requirements text for a control, reused by evidence
        detection, analysis and maturity assessment. Empty string when no
        context builder is wired (tests without an LLM)."""
        if self._context_builder is None:
            return ""
        assessment = self._db.get(AssessmentModel, control.assessment_id)
        context = self._context_builder.build(
            assessment.kb_collection, control.control_number, assessment.assessment_level
        )
        return ControlContextBuilder.to_prompt_text(context)

    def _detect_evidence(self, question_text: str, requirements_text: str) -> tuple[bool, list[str]]:
        """Ask the detector whether a document is relevant for this question.
        Defaults to 'no evidence expected' when the detector is absent."""
        if self._evidence_detector is None:
            return False, []
        try:
            return self._evidence_detector.is_evidence_expected(question_text, requirements_text)
        except Exception:  # noqa: BLE001
            # Evidence detection is a nicety, not a blocker — never fail the
            # whole control start because the detector hiccuped.
            return False, []
        

    def _generate_followup_questions(self, control: AssessmentControlModel) -> list[str]:
        """Real follow-up questions from the control's requirements, filtered by
        the assessment's declared Assessment Level.

        Falls back to placeholders when no LLM is wired in — that keeps the
        service usable in tests and without an API key. A failed LLM call is
        NOT swallowed: the caller gets an ExternalServiceError rather than
        silently-wrong placeholder questions being persisted forever.
        """
        if self._context_builder is None or self._question_generator is None:
            return [
                f"[Placeholder] Follow-up question {i + 1} for control "
                f"{control.control_number} — no LLM configured."
                for i in range(PLACEHOLDER_QUESTION_COUNT)
            ]

        assessment = self._db.get(AssessmentModel, control.assessment_id)
        context = self._context_builder.build(
            assessment.kb_collection, control.control_number, assessment.assessment_level
        )
        context_text = ControlContextBuilder.to_prompt_text(context)
        # The generator needs to know which tiers the AL unlocked, so it can
        # guarantee each one gets its own question instead of silently
        # dropping the highest tier when the budget is tight.
        section_labels = [label for label, _ in context.get("sections", [])]
        return self._question_generator.generate(
            control.control_number,
            context_text,
            assessment_level=assessment.assessment_level,
            section_labels=section_labels,
        )

    def start_control(self, control_id: UUID, user_id: UUID) -> AssessmentControlModel:
        control = self._get_owned_control(control_id, user_id)

        if control.followup_questions:
            # Already started — return as-is (idempotent, supports resume)
            return control

        assessment = self._db.get(AssessmentModel, control.assessment_id)
        questions = self._generate_followup_questions(control)
        requirements_text = self._control_requirements_text(control)
        for idx, q_text in enumerate(questions):
            if assessment.evidence_mode == "no_evidence":
                expected, docs = False, []
            else:
                expected, docs = self._detect_evidence(q_text, requirements_text)
            self._db.add(
                FollowupQuestionModel(
                    assessment_control_id=control.id,
                    question_text=q_text,
                    order_index=idx,
                    evidence_expected=expected,
                    expected_documents=json.dumps(docs) if docs else None,
                )
            )
        control.state = "in_progress"

        # Log bot messages for the conversation history
        self._db.add(
            ConversationMessageModel(
                assessment_id=control.assessment_id,
                role="bot",
                content=f"Control {control.control_number}: {control.title}",
            )
        )
        self._db.commit()
        self._db.refresh(control)
        return control

    # ── Answering ─────────────────────────────────────────────────────

    def _resolve_response(
        self,
        question: FollowupQuestionModel,
        response: str | None,
        raw_text: str | None,
        response_scale: str = "yes_no_partial",
    ) -> tuple[str, str | None]:
        """Decide the structured verdict for an answer.

        A button press (explicit response) always wins — the user's own
        classification is authoritative and costs nothing. The LLM is only
        consulted when the user typed free text and gave no verdict.
        Returns (response, justification).
        """
        allowed = {"yes", "no", "skipped"} if response_scale == "yes_no" else VALID_RESPONSES

        if response:
            if response not in allowed:
                raise ValidationError(f"response must be one of {sorted(allowed)}.")
            return response, None

        if not raw_text or not raw_text.strip():
            raise ValidationError("Provide either a response or raw_text.")

        if self._answer_classifier is None:
            raise ValidationError(
                "Free-text answers require a configured LLM. Send an explicit response instead."
            )
        return self._answer_classifier.classify(question.question_text, raw_text, response_scale)

    def answer_question(
        self, question_id: UUID, user_id: UUID, response: str | None, raw_text: str | None
    ) -> AnswerModel:
        question = self._db.get(FollowupQuestionModel, question_id)
        if question is None:
            raise NotFoundError("Question not found.")
        control = self._get_owned_control(question.assessment_control_id, user_id)

        if question.answer is not None:
            raise ConflictError("This question is already answered. Use edit to change it.")

        assessment = self._db.get(AssessmentModel, control.assessment_id)
        resolved, justification = self._resolve_response(
            question, response, raw_text, assessment.response_scale
        )

        answer = AnswerModel(
            followup_question_id=question.id,
            response=resolved,
            raw_text=raw_text,
            llm_justification=justification,
        )
        self._db.add(answer)

        # Conversation log: user's answer
        self._db.add(
            ConversationMessageModel(
                assessment_id=control.assessment_id,
                role="user",
                content=raw_text if raw_text else resolved,
                related_question_id=question.id,
            )
        )
        self._db.flush()

        self._maybe_complete_control(control)
        self._db.commit()
        self._db.refresh(answer)
        return answer

    def edit_answer(
        self, answer_id: UUID, user_id: UUID, response: str | None, raw_text: str | None
    ) -> AnswerModel:
        answer = self._db.get(AnswerModel, answer_id)
        if answer is None:
            raise NotFoundError("Answer not found.")
        question = self._db.get(FollowupQuestionModel, answer.followup_question_id)
        control = self._get_owned_control(question.assessment_control_id, user_id)

        assessment = self._db.get(AssessmentModel, control.assessment_id)
        resolved, justification = self._resolve_response(
            question, response, raw_text, assessment.response_scale
        )

        answer.response = resolved
        answer.raw_text = raw_text
        answer.llm_justification = justification

        self._db.add(
            ConversationMessageModel(
                assessment_id=control.assessment_id,
                role="user",
                content=f"(edited) {raw_text if raw_text else resolved}",
                related_question_id=question.id,
                related_answer_id=answer.id,
            )
        )
        self._db.flush()
        self._maybe_complete_control(control)
        self._db.commit()
        self._db.refresh(answer)
        return answer

    def _maybe_complete_control(self, control: AssessmentControlModel) -> None:
        """A control becomes 'answered' once every followup question has an
        answer. We query answer counts directly rather than reading the
        cached `control.followup_questions` relationship, which can be stale
        within the same transaction right after a flush()."""
        q_ids_stmt = select(FollowupQuestionModel.id).where(
            FollowupQuestionModel.assessment_control_id == control.id
        )
        question_ids = [row[0] for row in self._db.execute(q_ids_stmt).all()]
        if not question_ids:
            return

        answered_stmt = select(AnswerModel.followup_question_id).where(
            AnswerModel.followup_question_id.in_(question_ids)
        )
        answered_ids = {row[0] for row in self._db.execute(answered_stmt).all()}

        if len(answered_ids) >= len(question_ids):
            control.state = "answered"
        elif control.state == "not_started":
            control.state = "in_progress"

    # ── Skipping ──────────────────────────────────────────────────────

    def skip_control(self, control_id: UUID, user_id: UUID) -> AssessmentControlModel:
        control = self._get_owned_control(control_id, user_id)
        control.state = "skipped"
        self._db.add(
            ConversationMessageModel(
                assessment_id=control.assessment_id,
                role="user",
                content=f"[Skipped control {control.control_number}]",
            )
        )
        self._db.commit()
        self._db.refresh(control)
        return control

    # ── Conversation history ──────────────────────────────────────────

    def get_messages(self, assessment_id: UUID, user_id: UUID) -> list[ConversationMessageModel]:
        self._get_owned_assessment(assessment_id, user_id)
        stmt = (
            select(ConversationMessageModel)
            .where(ConversationMessageModel.assessment_id == assessment_id)
            .order_by(ConversationMessageModel.created_at)
        )
        return list(self._db.execute(stmt).scalars().all())
    
    # ── Evidence (Phase 5) ────────────────────────────────────────────

    def _get_owned_answer(self, answer_id: UUID, user_id: UUID) -> AnswerModel:
        answer = self._db.get(AnswerModel, answer_id)
        if answer is None:
            raise NotFoundError("Answer not found.")
        question = self._db.get(FollowupQuestionModel, answer.followup_question_id)
        self._get_owned_control(question.assessment_control_id, user_id)
        return answer

    def upload_evidence(
        self,
        answer_id: UUID,
        user_id: UUID,
        filename: str,
        file_type: str,
        content: bytes,
    ) -> EvidenceModel:
        """Store an uploaded document for an answer and extract its text.
        The document is analysed separately (analyze_evidence) so a slow or
        failing LLM call never blocks the upload itself."""
        if self._storage is None:
            raise ValidationError("File storage is not configured.")

        answer = self._get_owned_answer(answer_id, user_id)
        question = self._db.get(FollowupQuestionModel, answer.followup_question_id)
        control = self._db.get(AssessmentControlModel, question.assessment_control_id)

        # Extract text now so an unreadable file is rejected immediately.
        extracted = extract_text(content, file_type)

        sha = hashlib.sha256(content).hexdigest()
        key = f"assessment_{control.assessment_id}/control_{control.control_number}/{sha[:12]}_{filename}"
        self._storage.save(key, content)

        evidence = EvidenceModel(
            answer_id=answer.id,
            storage_key=key,
            filename=filename,
            file_type=file_type,
            size=len(content),
            sha256=sha,
            extracted_text=extracted,
        )
        self._db.add(evidence)
        self._db.add(
            ConversationMessageModel(
                assessment_id=control.assessment_id,
                role="user",
                content=f"[Uploaded evidence: {filename}]",
                related_answer_id=answer.id,
            )
        )
        self._db.commit()
        self._db.refresh(evidence)
        return evidence

    def analyze_evidence(self, evidence_id: UUID, user_id: UUID) -> EvidenceModel:
        """Run the LLM auditor over an uploaded document and persist its
        verdict. Idempotent-ish: re-analysing replaces the previous analysis."""
        if self._evidence_analyzer is None:
            raise ValidationError("Evidence analysis requires a configured LLM.")

        evidence = self._db.get(EvidenceModel, evidence_id)
        if evidence is None:
            raise NotFoundError("Evidence not found.")
        answer = self._get_owned_answer(evidence.answer_id, user_id)
        question = self._db.get(FollowupQuestionModel, answer.followup_question_id)
        control = self._db.get(AssessmentControlModel, question.assessment_control_id)
        assessment = self._db.get(AssessmentModel, control.assessment_id)

        requirements_text = self._control_requirements_text(control)
        declared = f"{question.question_text} -> {answer.response}"
        if answer.raw_text:
            declared += f" ({answer.raw_text})"

        result = self._evidence_analyzer.analyze(
            control_question=control.title,
            requirements_text=requirements_text,
            declared_answers=declared,
            evidence_text=evidence.extracted_text or "",
            target_maturity=assessment.target_maturity_level,
        )

        # Replace any previous analysis for this evidence.
        if evidence.analysis is not None:
            self._db.delete(evidence.analysis)
            self._db.flush()

        analysis = EvidenceAnalysisModel(
            evidence_id=evidence.id,
            verdict=result["verdict"],
            relevance=result["relevance"],
            coverage=json.dumps(result["coverage"]) if result["coverage"] else None,
            summary=result["summary"],
            missing_elements=json.dumps(result["missing_elements"]) if result["missing_elements"] else None,
        )
        self._db.add(analysis)
        self._db.commit()
        self._db.refresh(evidence)
        return evidence
    


    # ── Maturity assessment (Phase 6) ─────────────────────────────────

    def _derive_control_evidence_status(self, control: AssessmentControlModel) -> EvidenceStatus:
        """Combine the evidence verdicts of all the control's answers into ONE
        status for the whole control, the way an auditor weighs all documents
        together. Severity/precedence order (worst and highest-tier win):
          contradicted  > improvement_confirmed > measurement_confirmed >
          confirmed > partially_confirmed > irrelevant > missing/none.
        'missing' applies only when a document was expected but not provided.
        """
        q_ids_stmt = select(FollowupQuestionModel.id, FollowupQuestionModel.evidence_expected).where(
            FollowupQuestionModel.assessment_control_id == control.id
        )
        rows = list(self._db.execute(q_ids_stmt).all())
        question_ids = [r[0] for r in rows]
        any_expected = any(r[1] for r in rows)
        if not question_ids:
            return EvidenceStatus.NOT_REQUIRED

        # Collect verdicts from evidence attached to this control's answers.
        answers_stmt = select(AnswerModel.id).where(
            AnswerModel.followup_question_id.in_(question_ids)
        )
        answer_ids = [r[0] for r in self._db.execute(answers_stmt).all()]
        verdicts: list[str] = []
        if answer_ids:
            ev_stmt = select(EvidenceAnalysisModel.verdict).join(
                EvidenceModel, EvidenceModel.id == EvidenceAnalysisModel.evidence_id
            ).where(EvidenceModel.answer_id.in_(answer_ids))
            verdicts = [r[0] for r in self._db.execute(ev_stmt).all()]

        if not verdicts:
            # No evidence analysed. Was any expected?
            return EvidenceStatus.MISSING if any_expected else EvidenceStatus.NOT_REQUIRED

        precedence = [
            ("contradicted", EvidenceStatus.CONTRADICTED),
            ("improvement_confirmed", EvidenceStatus.IMPROVEMENT_CONFIRMED),
            ("measurement_confirmed", EvidenceStatus.MEASUREMENT_CONFIRMED),
            ("confirmed", EvidenceStatus.CONFIRMED),
            ("partially_confirmed", EvidenceStatus.PARTIALLY_CONFIRMED),
            ("irrelevant", EvidenceStatus.IRRELEVANT),
        ]
        for verdict_name, status in precedence:
            if verdict_name in verdicts:
                return status
        return EvidenceStatus.MISSING if any_expected else EvidenceStatus.NOT_REQUIRED

    def assess_control(self, control_id: UUID, user_id: UUID) -> AssessmentControlModel:
        """Run the Maturity Assessment Engine on one control and persist the
        result (ML, confidence, mode, finding, recommendation). Computed once
        and stored — the report never recomputes it."""
        if self._maturity_engine is None:
            raise ValidationError("Maturity assessment requires a configured LLM.")

        control = self._get_owned_control(control_id, user_id)
        assessment = self._db.get(AssessmentModel, control.assessment_id)

        if control.state == "skipped":
            raise ValidationError("Skipped controls are excluded from maturity scoring.")

        # Gather the control's answers.
        q_stmt = select(FollowupQuestionModel.id).where(
            FollowupQuestionModel.assessment_control_id == control.id
        )
        question_ids = [r[0] for r in self._db.execute(q_stmt).all()]
        if not question_ids:
            raise ValidationError("Control has no questions to assess. Start it first.")

        # Paired question+answer view, in question order — gives the LLM
        # what was actually asked, not just a bag of "yes"/"no" values with
        # no context on how much of the control's scope they cover.
        qa_stmt = (
            select(FollowupQuestionModel.question_text, AnswerModel.response)
            .join(AnswerModel, AnswerModel.followup_question_id == FollowupQuestionModel.id)
            .where(FollowupQuestionModel.assessment_control_id == control.id)
            .order_by(FollowupQuestionModel.order_index)
        )
        qa_pairs = [(r[0], r[1]) for r in self._db.execute(qa_stmt).all()]
        responses = [r[1] for r in qa_pairs]
        if not responses:
            raise ValidationError("Control has no answers yet.")

        evidence_status = self._derive_control_evidence_status(control)
        requirements_text = self._control_requirements_text(control)

        result = self._maturity_engine.assess(
            control_number=control.control_number,
            control_question=control.title,
            requirements_text=requirements_text,
            responses=responses,
            evidence_status=evidence_status,
            target=assessment.target_maturity_level,
            qa_pairs=qa_pairs,
        )

        # Recommendation (deterministic shortcuts + LLM where useful).
        recommendation = ""
        if self._recommendation is not None:
            recommendation = self._recommendation.generate(
                control_number=control.control_number,
                control_title=control.title,
                maturity_level=result["maturity_level"],
                target=assessment.target_maturity_level,
                evidence_status=result["evidence_status"],
                missing_for_next_level=result["missing_for_next_level"],
            )

        # Persist the result on the control.
        control.maturity_score = float(result["maturity_level"])
        control.confidence = result["confidence"]
        control.assessment_mode = result["assessment_mode"]
        control.evidence_status = result["evidence_status"]
        control.finding = result["finding"]
        control.missing_for_next_level = result["missing_for_next_level"]
        control.recommendation = recommendation
        control.state = "completed"
        from datetime import datetime, timezone
        control.assessed_at = datetime.now(timezone.utc)

        self._db.commit()
        self._db.refresh(control)
        return control
    def build_report(self, assessment_id, user_id):
        from app.application.services.report_service import ReportService
        assessment = self._get_owned_assessment(assessment_id, user_id)
        controls = self._controls_ordered(assessment_id)
        rs = ReportService(target=assessment.target_maturity_level)
        return rs.build_report(assessment, controls)