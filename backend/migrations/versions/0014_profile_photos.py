"""Add protected profile photos to employee cards."""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("employees") as batch:
        batch.add_column(sa.Column("photo_stored_name", sa.String(50), nullable=True))
        batch.add_column(sa.Column("photo_content_type", sa.String(30), nullable=True))
        batch.add_column(sa.Column("photo_size", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("photo_version", sa.Integer(), nullable=False, server_default="0")
        )
        batch.create_unique_constraint("uq_employees_photo_stored_name", ["photo_stored_name"])
        batch.create_check_constraint(
            "ck_employees_profile_photo",
            "(photo_stored_name IS NULL AND photo_content_type IS NULL AND photo_size IS NULL) OR "
            "(photo_stored_name IS NOT NULL AND photo_content_type IS NOT NULL "
            "AND photo_size > 0 AND photo_size <= 5242880)",
        )


def downgrade():
    with op.batch_alter_table("employees") as batch:
        batch.drop_constraint("ck_employees_profile_photo", type_="check")
        batch.drop_constraint("uq_employees_photo_stored_name", type_="unique")
        batch.drop_column("photo_version")
        batch.drop_column("photo_size")
        batch.drop_column("photo_content_type")
        batch.drop_column("photo_stored_name")
