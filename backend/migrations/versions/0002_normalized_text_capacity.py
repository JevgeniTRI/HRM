"""Allow normalized strings to expand without truncating accepted inputs."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    # Unicode casefold can expand one character to three; search includes both name orders.
    for table in ("departments", "skills"):
        with op.batch_alter_table(table) as batch:
            batch.alter_column("name_key", existing_type=sa.String(100), type_=sa.String(300))
    with op.batch_alter_table(
        "employees",
        table_args=(
            sa.CheckConstraint(
                "status IN ('active', 'probation', 'leave', 'inactive')", name="ck_employees_status"
            ),
        ),
    ) as batch:
        batch.alter_column("search_text", existing_type=sa.String(600), type_=sa.String(720))


def downgrade():
    for table in ("departments", "skills"):
        with op.batch_alter_table(table) as batch:
            batch.alter_column("name_key", existing_type=sa.String(300), type_=sa.String(100))
    with op.batch_alter_table("employees") as batch:
        batch.alter_column("search_text", existing_type=sa.String(720), type_=sa.String(600))
