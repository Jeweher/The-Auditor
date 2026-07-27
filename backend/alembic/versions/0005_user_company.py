"""add company_name and sector to users

Revision ID: 0005_user_company
Revises: 0004_phase5_6
Create Date: 2026-07-19

"""
from alembic import op
import sqlalchemy as sa

revision = "0005_user_company"
down_revision = "0004_phase5_6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("company_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("sector", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "sector")
    op.drop_column("users", "company_name")