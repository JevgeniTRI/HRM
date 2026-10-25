"""Per-skill numeric or letter scales and descriptions, preserving existing scores."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def check_column(constraint, _table):
    return "current_level" if "current_level" in str(constraint.sqltext) else "target_level"


def replace_assessment_limits(current_max: int, target_min: int, target_max: int):
    with op.batch_alter_table(
        "employee_skills",
        naming_convention={
            "ck": "ck_%(table_name)s_%(level_column)s",
            "level_column": check_column,
        },
    ) as batch:
        batch.drop_constraint("ck_employee_skills_current_level", type_="check")
        batch.drop_constraint("ck_employee_skills_target_level", type_="check")
        batch.create_check_constraint(
            "ck_employee_skills_current_level",
            f"current_level IS NULL OR current_level BETWEEN 0 AND {current_max}",
        )
        batch.create_check_constraint(
            "ck_employee_skills_target_level", f"target_level BETWEEN {target_min} AND {target_max}"
        )


def upgrade():
    with op.batch_alter_table("skills") as batch:
        batch.add_column(
            sa.Column("scale_type", sa.String(10), nullable=False, server_default="numeric")
        )
        batch.add_column(sa.Column("scale_min", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("scale_max", sa.Integer(), nullable=False, server_default="5"))
        batch.add_column(
            sa.Column("level_descriptions", sa.JSON(), nullable=False, server_default="{}")
        )
        batch.create_check_constraint(
            "ck_skills_scale",
            "scale_min >= 0 AND scale_min <= scale_max AND "
            "((scale_type = 'numeric' AND scale_max <= 10) OR "
            "(scale_type = 'letter' AND scale_max <= 25))",
        )
    skills = sa.table("skills", sa.column("level_descriptions", sa.JSON()))
    op.execute(
        skills.update().values(
            level_descriptions={
                "0": "Нет опыта",
                "1": "Начальный",
                "2": "Базовый",
                "3": "Уверенный",
                "4": "Продвинутый",
                "5": "Эксперт",
            }
        )
    )
    replace_assessment_limits(25, 0, 25)


def downgrade():
    replace_assessment_limits(5, 1, 5)
    with op.batch_alter_table("skills") as batch:
        batch.drop_constraint("ck_skills_scale", type_="check")
        for name in ("level_descriptions", "scale_max", "scale_min", "scale_type"):
            batch.drop_column(name)
