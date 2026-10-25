"""Allow certificates up to 15 MiB while preserving existing records."""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def set_size_limit(limit: int):
    # Give the original unnamed CHECK a name so batch mode can replace it.
    with op.batch_alter_table(
        "certificates", naming_convention={"ck": "ck_%(table_name)s_size"}
    ) as batch:
        batch.drop_constraint("ck_certificates_size", type_="check")
        batch.create_check_constraint("ck_certificates_size", f"size > 0 AND size <= {limit}")


def upgrade():
    set_size_limit(15 * 1024 * 1024)


def downgrade():
    set_size_limit(10 * 1024 * 1024)
