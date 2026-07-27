"""phase 5+6: target maturity, control results, evidence analysis

Revision ID: 0004_phase5_6
Revises: 0003_assessment_level
Create Date: 2026-07-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_phase5_6"
down_revision = "0003_assessment_level"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- assessments: declared target maturity level ---
    op.add_column(
        "assessments",
        sa.Column("target_maturity_level", sa.Integer(), nullable=False, server_default="3"),
    )

    # --- assessment_controls: persisted assessment results ---
    op.add_column("assessment_controls", sa.Column("confidence", sa.String(length=16), nullable=True))
    op.add_column("assessment_controls", sa.Column("assessment_mode", sa.String(length=16), nullable=True))
    op.add_column("assessment_controls", sa.Column("evidence_status", sa.String(length=32), nullable=True))
    op.add_column("assessment_controls", sa.Column("finding", sa.Text(), nullable=True))
    op.add_column("assessment_controls", sa.Column("missing_for_next_level", sa.Text(), nullable=True))
    op.add_column("assessment_controls", sa.Column("recommendation", sa.Text(), nullable=True))
    op.add_column("assessment_controls", sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=True))

    # --- followup_questions: evidence expectation ---
    op.add_column(
        "followup_questions",
        sa.Column("evidence_expected", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("followup_questions", sa.Column("expected_documents", sa.Text(), nullable=True))

    # --- evidence: rework to storage_key + sha256, drop old columns ---
    op.add_column("evidence", sa.Column("storage_key", sa.String(length=1024), nullable=False, server_default=""))
    op.add_column("evidence", sa.Column("sha256", sa.String(length=64), nullable=True))
    op.drop_column("evidence", "file_path")
    op.drop_column("evidence", "llm_analysis")

    # --- new table: evidence_analysis ---
    op.create_table(
        "evidence_analysis",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidence.id"), nullable=False, unique=True),
        sa.Column("verdict", sa.String(length=32), nullable=False),
        sa.Column("relevance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("coverage", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("missing_elements", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_evidence_analysis_evidence_id", "evidence_analysis", ["evidence_id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_analysis_evidence_id", table_name="evidence_analysis")
    op.drop_table("evidence_analysis")

    op.add_column("evidence", sa.Column("llm_analysis", sa.Text(), nullable=True))
    op.add_column("evidence", sa.Column("file_path", sa.String(length=1024), nullable=False, server_default=""))
    op.drop_column("evidence", "sha256")
    op.drop_column("evidence", "storage_key")

    op.drop_column("followup_questions", "expected_documents")
    op.drop_column("followup_questions", "evidence_expected")

    op.drop_column("assessment_controls", "assessed_at")
    op.drop_column("assessment_controls", "recommendation")
    op.drop_column("assessment_controls", "missing_for_next_level")
    op.drop_column("assessment_controls", "finding")
    op.drop_column("assessment_controls", "evidence_status")
    op.drop_column("assessment_controls", "assessment_mode")
    op.drop_column("assessment_controls", "confidence")

    op.drop_column("assessments", "target_maturity_level")