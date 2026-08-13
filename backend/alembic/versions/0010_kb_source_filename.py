"""add kb_source_filename to assessments

Revision ID: 0010_kb_source_filename
Revises: 0009_assessment_options
Create Date: 2026-08-12

"""
from alembic import op
import sqlalchemy as sa

revision = "0010_kb_source_filename"
down_revision = "0009_assessment_options"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column("kb_source_filename", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessments", "kb_source_filename")