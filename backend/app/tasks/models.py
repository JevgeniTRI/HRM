from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Column, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models import Department, Employee, utc_now
from app.services.task_rules import from_hundredths, person_hours

task_departments = Table(
    "task_departments",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "department_id",
        ForeignKey("departments.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    ),
)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("status IN ('todo', 'in_progress', 'done')", name="ck_tasks_status"),
        CheckConstraint(
            "(learning_source IS NULL AND learning_format IS NULL AND participant_count IS NULL "
            "AND duration_hundredths IS NULL) OR "
            "(learning_source IS NOT NULL AND learning_source IN ('internal', 'external') "
            "AND learning_format IS NOT NULL AND learning_format IN ('individual', 'group') "
            "AND participant_count IS NOT NULL AND participant_count BETWEEN 1 AND 10000 "
            "AND ((learning_format = 'individual' AND participant_count = 1) "
            "OR (learning_format = 'group' AND participant_count >= 2)))",
            name="ck_tasks_learning",
        ),
        CheckConstraint(
            "duration_hundredths IS NULL OR duration_hundredths BETWEEN 1 AND 1000000",
            name="ck_tasks_duration",
        ),
        CheckConstraint(
            "(cost_minor IS NULL AND currency IS NULL) OR "
            "(cost_minor IS NOT NULL AND cost_minor BETWEEN 0 AND 99999999999 "
            "AND currency IS NOT NULL AND currency IN ('EUR', 'USD', 'UAH', 'GBP'))",
            name="ck_tasks_cost",
        ),
        CheckConstraint("version >= 1", name="ck_tasks_version"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"), index=True
    )
    assignee: Mapped[Employee | None] = relationship()
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    search_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="todo", index=True)
    learning_source: Mapped[str | None] = mapped_column(String(20))
    learning_format: Mapped[str | None] = mapped_column(String(20))
    participant_count: Mapped[int | None]
    duration_hundredths: Mapped[int | None]
    cost_minor: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str | None] = mapped_column(String(3))
    due_on: Mapped[date | None]
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now)
    version: Mapped[int] = mapped_column(default=1)
    departments: Mapped[list[Department]] = relationship(
        secondary=task_departments, passive_deletes=True
    )

    __mapper_args__ = {"version_id_col": version}

    @property
    def assignee_name(self) -> str | None:
        return f"{self.assignee.first_name} {self.assignee.last_name}" if self.assignee else None

    @property
    def duration_hours(self) -> Decimal | None:
        return from_hundredths(self.duration_hundredths)

    @property
    def cost(self) -> Decimal | None:
        return from_hundredths(self.cost_minor)

    @property
    def person_hours(self) -> Decimal | None:
        return person_hours(self.duration_hundredths, self.participant_count)
