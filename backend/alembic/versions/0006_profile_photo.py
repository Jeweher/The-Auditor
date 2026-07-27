"""add profile_photo to users

Revision ID: 0006_profile_photo
Revises: 0005_user_company
Create Date: 2026-07-24

"""
from alembic import op
import sqlalchemy as sa

revision = "0006_profile_photo"
down_revision = "0005_user_company"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("profile_photo", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "profile_photo")