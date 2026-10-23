"""Tasks, training effort, exact costs, and multi-department assignments."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("learning_source", sa.String(20), nullable=True),
        sa.Column("learning_format", sa.String(20), nullable=True),
        sa.Column("participant_count", sa.Integer(), nullable=True),
        sa.Column("duration_hundredths", sa.Integer(), nullable=True),
        sa.Column("cost_minor", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("status IN ('todo', 'in_progress', 'done')", name="ck_tasks_status"),
        sa.CheckConstraint(
            "(learning_source IS NULL AND learning_format IS NULL AND participant_count IS NULL "
            "AND duration_hundredths IS NULL) OR "
            "(learning_source IS NOT NULL AND learning_source IN ('internal', 'external') "
            "AND learning_format IS NOT NULL AND learning_format IN ('individual', 'group') "
            "AND participant_count IS NOT NULL AND participant_count BETWEEN 1 AND 10000 "
            "AND ((learning_format = 'individual' AND participant_count = 1) "
            "OR (learning_format = 'group' AND participant_count >= 2)))",
            name="ck_tasks_learning",
        ),
        sa.CheckConstraint(
            "duration_hundredths IS NULL OR duration_hundredths BETWEEN 1 AND 1000000",
            name="ck_tasks_duration",
        ),
        sa.CheckConstraint(
            "(cost_minor IS NULL AND currency IS NULL) OR "
            "(cost_minor IS NOT NULL AND cost_minor BETWEEN 0 AND 99999999999 "
            "AND currency IS NOT NULL AND currency IN ('EUR', 'USD', 'UAH', 'GBP'))",
            name="ck_tasks_cost",
        ),
        sa.CheckConstraint("version >= 1", name="ck_tasks_version"),
    )
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_table(
        "task_departments",
        sa.Column(
            "task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "department_id",
            sa.Integer(),
            sa.ForeignKey("departments.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )
    op.create_index("ix_task_departments_department_id", "task_departments", ["department_id"])


def downgrade():
    op.drop_table("task_departments")
    op.drop_table("tasks")
