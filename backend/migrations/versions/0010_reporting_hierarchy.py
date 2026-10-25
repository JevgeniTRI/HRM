"""Explicit managers and reporting lines; retain existing people and roles."""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("employees") as batch:
        batch.add_column(sa.Column("is_manager", sa.Boolean(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("manager_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_employees_manager", "employees", ["manager_id"], ["id"], ondelete="RESTRICT"
        )
        batch.create_index("ix_employees_manager_id", ["manager_id"])
        batch.create_check_constraint(
            "ck_employees_not_own_manager", "manager_id IS NULL OR manager_id != id"
        )
    op.execute(
        sa.text(
            "UPDATE employees SET is_manager = 1 WHERE id IN "
            "(SELECT employee_id FROM accounts WHERE role = 'manager')"
        )
    )


def downgrade():
    with op.batch_alter_table("employees") as batch:
        batch.drop_constraint("ck_employees_not_own_manager", type_="check")
        batch.drop_constraint("fk_employees_manager", type_="foreignkey")
        batch.drop_index("ix_employees_manager_id")
        batch.drop_column("manager_id")
        batch.drop_column("is_manager")
