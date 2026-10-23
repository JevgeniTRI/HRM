"""Accounts, revocable sessions and personal task assignments."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "activities",
        sa.Column("actor_username", sa.String(80), server_default="Система", nullable=False),
    )
    for name in ("about", "experience", "education"):
        op.add_column("employees", sa.Column(name, sa.Text(), server_default="", nullable=False))
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(80), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "role IN ('admin', 'power_user', 'manager', 'employee')", name="ck_accounts_role"
        ),
        sa.CheckConstraint(
            "role = 'admin' OR employee_id IS NOT NULL", name="ck_accounts_employee"
        ),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_sessions_account_id", "auth_sessions", ["account_id"])
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("assignee_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_tasks_assignee", "employees", ["assignee_id"], ["id"], ondelete="SET NULL"
        )
        batch.create_index("ix_tasks_assignee_id", ["assignee_id"])


def downgrade():
    op.drop_column("activities", "actor_username")
    with op.batch_alter_table("tasks") as batch:
        batch.drop_index("ix_tasks_assignee_id")
        batch.drop_constraint("fk_tasks_assignee", type_="foreignkey")
        batch.drop_column("assignee_id")
    op.drop_table("auth_sessions")
    op.drop_table("accounts")
    for name in ("education", "experience", "about"):
        op.drop_column("employees", name)
