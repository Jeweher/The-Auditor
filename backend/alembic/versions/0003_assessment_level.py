"""add assessment_level to assessments

Revision ID: 0003_assessment_level
Revises: 0002_assessment
Create Date: 2026-07-14

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_assessment_level"
down_revision = "0002_assessment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column("assessment_level", sa.String(length=8), nullable=False, server_default="AL1"),
    )


def downgrade() -> None:
    op.drop_column("assessments", "assessment_level")