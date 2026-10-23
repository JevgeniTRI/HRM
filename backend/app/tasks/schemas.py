from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.schemas import DepartmentRead, ORMModel
from app.services.task_rules import (
    Currency,
    LearningFormat,
    LearningSource,
    TaskStatus,
    validate_task,
)

Hours = Annotated[Decimal, Field(gt=0, le=10000, decimal_places=2, max_digits=7)]
Cost = Annotated[Decimal, Field(ge=0, le=Decimal("999999999.99"), decimal_places=2, max_digits=11)]


class TaskWrite(BaseModel):
    assignee_id: int | None = Field(default=None, gt=0)
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    description: str = Field(default="", max_length=5000)
    status: TaskStatus = TaskStatus.TODO
    learning_source: LearningSource | None = None
    learning_format: LearningFormat | None = None
    participant_count: int | None = Field(default=None, ge=1, le=10000, strict=True)
    duration_hours: Hours | None = None
    cost: Cost | None = None
    currency: Currency | None = None
    due_on: date | None = None
    department_ids: list[Annotated[int, Field(gt=0)]] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_training_and_cost(self):
        validate_task(
            learning_source=self.learning_source,
            learning_format=self.learning_format,
            participant_count=self.participant_count,
            duration_hours=self.duration_hours,
            cost=self.cost,
            currency=self.currency,
            department_ids=self.department_ids,
        )
        return self


class TaskUpdate(TaskWrite):
    version: int = Field(ge=1)


class TaskStatusWrite(BaseModel):
    status: TaskStatus
    version: int = Field(ge=1)


class TaskRead(ORMModel):
    assignee_id: int | None
    assignee_name: str | None
    id: int
    title: str
    description: str
    status: TaskStatus
    learning_source: LearningSource | None
    learning_format: LearningFormat | None
    participant_count: int | None
    duration_hours: Decimal | None
    person_hours: Decimal | None
    cost: Decimal | None
    currency: Currency | None
    due_on: date | None
    departments: list[DepartmentRead]
    version: int
    created_at: datetime
    updated_at: datetime


class TaskPage(BaseModel):
    items: list[TaskRead]
    total: int
    page: int
    page_size: int


class CurrencyTotal(BaseModel):
    currency: Currency
    amount: Decimal


class TaskSummary(BaseModel):
    total: int
    status_counts: dict[TaskStatus, int]
    person_hours: Decimal
    training_count: int
    unestimated_training_count: int
    costs: list[CurrencyTotal]
    without_cost_count: int


class EffortEstimate(BaseModel):
    duration_hours: Hours
    participant_count: int = Field(ge=1, le=10000, strict=True)


class EffortRead(BaseModel):
    person_hours: Decimal
