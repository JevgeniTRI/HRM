"""Separate level names from existing requirements without changing descriptions or scores."""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "skills", sa.Column("level_names", sa.JSON(), nullable=False, server_default="{}")
    )
    skills = sa.table(
        "skills",
        sa.column("id", sa.Integer()),
        sa.column("scale_type", sa.String()),
        sa.column("scale_min", sa.Integer()),
        sa.column("scale_max", sa.Integer()),
        sa.column("level_names", sa.JSON()),
    )
    defaults = ("Нет опыта", "Начальный", "Базовый", "Уверенный", "Продвинутый", "Эксперт")
    connection = op.get_bind()
    for skill in connection.execute(sa.select(skills)).mappings().all():
        names = {}
        for level in range(skill["scale_min"], skill["scale_max"] + 1):
            label = chr(65 + level) if skill["scale_type"] == "letter" else str(level)
            names[str(level)] = defaults[level] if level < len(defaults) else f"Уровень {label}"
        connection.execute(
            skills.update().where(skills.c.id == skill["id"]).values(level_names=names)
        )


def downgrade():
    with op.batch_alter_table("skills") as batch:
        batch.drop_column("level_names")
