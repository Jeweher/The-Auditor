"""create assessment engine tables

Revision ID: 0002_assessment
Revises: 0001_initial
Create Date: 2026-07-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002_assessment"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kb_collection", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="in_progress"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_assessments_user_id", "assessments", ["user_id"])

    op.create_table(
        "assessment_controls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id"), nullable=False),
        sa.Column("control_number", sa.String(length=32), nullable=False),
        sa.Column("domain", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="not_started"),
        sa.Column("maturity_score", sa.Float(), nullable=True),
    )
    op.create_index("ix_assessment_controls_assessment_id", "assessment_controls", ["assessment_id"])

    op.create_table(
        "followup_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_control_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessment_controls.id"), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
    )
    op.create_index("ix_followup_questions_control_id", "followup_questions", ["assessment_control_id"])

    op.create_table(
        "answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("followup_question_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("followup_questions.id"), nullable=False, unique=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("response", sa.String(length=16), nullable=False),
        sa.Column("llm_justification", sa.Text(), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_answers_question_id", "answers", ["followup_question_id"])

    op.create_table(
        "conversation_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id"), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("related_question_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_answer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_conversation_messages_assessment_id", "conversation_messages", ["assessment_id"])

    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("answer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("answers.id"), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("file_type", sa.String(length=128), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("llm_analysis", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_evidence_answer_id", "evidence", ["answer_id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_answer_id", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index("ix_conversation_messages_assessment_id", table_name="conversation_messages")
    op.drop_table("conversation_messages")
    op.drop_index("ix_answers_question_id", table_name="answers")
    op.drop_table("answers")
    op.drop_index("ix_followup_questions_control_id", table_name="followup_questions")
    op.drop_table("followup_questions")
    op.drop_index("ix_assessment_controls_assessment_id", table_name="assessment_controls")
    op.drop_table("assessment_controls")
    op.drop_index("ix_assessments_user_id", table_name="assessments")
    op.drop_table("assessments")