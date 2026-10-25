"""Add optional training periods for the learning calendar."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("start_on", sa.Date(), nullable=True))
        batch.add_column(sa.Column("end_on", sa.Date(), nullable=True))
        batch.create_check_constraint(
            "ck_tasks_training_dates",
            "(start_on IS NULL AND end_on IS NULL) OR "
            "(learning_source IS NOT NULL AND start_on IS NOT NULL "
            "AND end_on IS NOT NULL AND end_on >= start_on)",
        )


def downgrade():
    with op.batch_alter_table("tasks") as batch:
        batch.drop_constraint("ck_tasks_training_dates", type_="check")
        batch.drop_column("end_on")
        batch.drop_column("start_on")
