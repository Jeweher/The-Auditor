"""
File: app/infrastructure/db/models.py
Folder: backend/app/infrastructure/db
Purpose: SQLAlchemy ORM models. This is the only file where table schemas
         are defined. Later phases (Assessment, Evidence, Report) add their
         models here too, each in its own migration.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.session import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    profile_photo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="user", nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    refresh_tokens: Mapped[list["RefreshTokenModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    email_verifications: Mapped[list["EmailVerificationModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    hashed_token: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["UserModel"] = relationship(back_populates="refresh_tokens")


# ─────────────────────────────────────────────────────────────────────
# Phase 3 — Assessment Engine
# ─────────────────────────────────────────────────────────────────────

class AssessmentModel(Base):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kb_collection: Mapped[str] = mapped_column(String(255), nullable=False)
    assessment_level: Mapped[str] = mapped_column(String(8), default="AL1", nullable=False)
    target_maturity_level: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="in_progress", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    controls: Mapped[list["AssessmentControlModel"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )
    messages: Mapped[list["ConversationMessageModel"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class AssessmentControlModel(Base):
    __tablename__ = "assessment_controls"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False, index=True
    )
    control_number: Mapped[str] = mapped_column(String(32), nullable=False)
    domain: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="not_started", nullable=False)
    maturity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Phase 6 — assessment results (persisted once, never recomputed for display)
    confidence: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    assessment_mode: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    evidence_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    finding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    missing_for_next_level: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    assessment: Mapped["AssessmentModel"] = relationship(back_populates="controls")
    followup_questions: Mapped[list["FollowupQuestionModel"]] = relationship(
        back_populates="control", cascade="all, delete-orphan"
    )


class FollowupQuestionModel(Base):
    __tablename__ = "followup_questions"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_control_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("assessment_controls.id"), nullable=False, index=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_expected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expected_documents: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list

    control: Mapped["AssessmentControlModel"] = relationship(back_populates="followup_questions")
    answer: Mapped[Optional["AnswerModel"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", uselist=False
    )


class AnswerModel(Base):
    __tablename__ = "answers"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    followup_question_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("followup_questions.id"), nullable=False, unique=True, index=True
    )
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response: Mapped[str] = mapped_column(String(16), nullable=False)  # yes|no|partial|skipped
    llm_justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    question: Mapped["FollowupQuestionModel"] = relationship(back_populates="answer")
    evidence: Mapped[list["EvidenceModel"]] = relationship(
        back_populates="answer", cascade="all, delete-orphan"
    )


class ConversationMessageModel(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # bot | user
    content: Mapped[str] = mapped_column(Text, nullable=False)
    related_question_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    related_answer_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    assessment: Mapped["AssessmentModel"] = relationship(back_populates="messages")


class EvidenceModel(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    answer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("answers.id"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    answer: Mapped["AnswerModel"] = relationship(back_populates="evidence")
    analysis: Mapped[Optional["EvidenceAnalysisModel"]] = relationship(
        back_populates="evidence", cascade="all, delete-orphan", uselist=False
    )


class EvidenceAnalysisModel(Base):
    __tablename__ = "evidence_analysis"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("evidence.id"), nullable=False, unique=True, index=True
    )
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)  # confirmed | partially_confirmed | ...
    relevance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coverage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: {must, should, protection}
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    missing_elements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    evidence: Mapped["EvidenceModel"] = relationship(back_populates="analysis")

    # ─────────────────────────────────────────────────────────────────────
# Email verification (registration confirmation, 6-digit code)
# ─────────────────────────────────────────────────────────────────────

class EmailVerificationModel(Base):
    __tablename__ = "email_verifications"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    hashed_code: Mapped[str] = mapped_column(String(255), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["UserModel"] = relationship(back_populates="email_verifications")


class AdminInvitationModel(Base):
    __tablename__ = "admin_invitations"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hashed_token: Mapped[str] = mapped_column(String(255), nullable=False)
    invited_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )