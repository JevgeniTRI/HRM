"""External identities, revocable integration credentials and import journal."""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "import_identities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("entity", sa.String(20), nullable=False),
        sa.Column("external_id", sa.String(120), nullable=False),
        sa.Column(
            "department_id", sa.Integer(), sa.ForeignKey("departments.id", ondelete="CASCADE")
        ),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE")),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE")),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id", ondelete="CASCADE")),
        sa.UniqueConstraint("source", "entity", "external_id"),
        sa.UniqueConstraint("source", "department_id"),
        sa.UniqueConstraint("source", "employee_id"),
        sa.UniqueConstraint("source", "team_id"),
        sa.UniqueConstraint("source", "skill_id"),
        sa.CheckConstraint(
            "(entity = 'departments' AND department_id IS NOT NULL "
            "AND employee_id IS NULL AND team_id IS NULL AND skill_id IS NULL) OR "
            "(entity = 'employees' AND employee_id IS NOT NULL "
            "AND department_id IS NULL AND team_id IS NULL AND skill_id IS NULL) OR "
            "(entity = 'teams' AND team_id IS NOT NULL "
            "AND department_id IS NULL AND employee_id IS NULL AND skill_id IS NULL) OR "
            "(entity = 'skills' AND skill_id IS NOT NULL "
            "AND department_id IS NULL AND employee_id IS NULL AND team_id IS NULL)",
            name="ck_import_identity_target",
        ),
    )
    op.create_table(
        "integration_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("prefix", sa.String(20), nullable=False),
        sa.Column("entities", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "import_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("request_id", sa.String(120), nullable=False),
        sa.Column("channel", sa.String(10), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("actor_username", sa.String(80), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source", "request_id"),
    )


def downgrade():
    op.drop_table("import_runs")
    op.drop_table("integration_keys")
    op.drop_table("import_identities")
