"""Stable teams and memberships, preserving existing reporting lines."""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "department_id",
            sa.Integer(),
            sa.ForeignKey("departments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "manager_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column(
            "supervisor_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="RESTRICT")
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_teams_department_id", "teams", ["department_id"])
    with op.batch_alter_table("employees") as batch:
        batch.add_column(sa.Column("team_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_employees_team", "teams", ["team_id"], ["id"], ondelete="RESTRICT"
        )
        batch.create_index("ix_employees_team_id", ["team_id"])


def downgrade():
    with op.batch_alter_table("employees") as batch:
        batch.drop_index("ix_employees_team_id")
        batch.drop_constraint("fk_employees_team", type_="foreignkey")
        batch.drop_column("team_id")
    op.drop_index("ix_teams_department_id", "teams")
    op.drop_table("teams")
