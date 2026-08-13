"""add job_title, company_size, audit_reason to users

Revision ID: 0011_user_profile_fields
Revises: 0010_kb_source_filename
Create Date: 2026-08-13

"""
from alembic import op
import sqlalchemy as sa

revision = "0011_user_profile_fields"
down_revision = "0010_kb_source_filename"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("job_title", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("company_size", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("audit_reason", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "audit_reason")
    op.drop_column("users", "company_size")
    op.drop_column("users", "job_title")