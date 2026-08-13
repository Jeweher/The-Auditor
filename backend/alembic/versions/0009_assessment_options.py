"""add evidence_mode, response_scale, sample_percent to assessments

Revision ID: 0009_assessment_options
Revises: 0008_admin_roles
Create Date: 2026-08-09

"""
from alembic import op
import sqlalchemy as sa

revision = "0009_assessment_options"
down_revision = "0008_admin_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column(
            "evidence_mode",
            sa.String(length=20),
            nullable=False,
            server_default="with_evidence",
        ),
    )
    op.add_column(
        "assessments",
        sa.Column(
            "response_scale",
            sa.String(length=20),
            nullable=False,
            server_default="yes_no_partial",
        ),
    )
    op.add_column(
        "assessments",
        sa.Column("sample_percent", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessments", "sample_percent")
    op.drop_column("assessments", "response_scale")
    op.drop_column("assessments", "evidence_mode")