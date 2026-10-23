"""Certificates attached to an employee's skill."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "certificates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "employee_skill_id",
            sa.Integer(),
            sa.ForeignKey("employee_skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("stored_name", sa.String(50), nullable=False, unique=True),
        sa.Column("content_type", sa.String(30), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("size > 0 AND size <= 10485760"),
    )
    op.create_index("ix_certificates_employee_skill_id", "certificates", ["employee_skill_id"])


def downgrade():
    op.drop_table("certificates")
