from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.services.assessment_rules import AssessmentState

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DepartmentWrite(BaseModel):
    name: Name
    description: str = Field(default="", max_length=2000)


class DepartmentRead(ORMModel):
    id: int
    name: str
    description: str


class DepartmentManager(BaseModel):
    id: int
    name: str


class DepartmentSummary(DepartmentRead):
    employee_count: int
    managers: list[DepartmentManager] = Field(default_factory=list)


class EmployeeStatus(StrEnum):
    ACTIVE = "active"
    PROBATION = "probation"
    LEAVE = "leave"
    INACTIVE = "inactive"


class EmployeeWrite(BaseModel):
    about: str = Field(default="", max_length=5000)
    experience: str = Field(default="", max_length=10000)
    education: str = Field(default="", max_length=5000)
    first_name: PersonName
    last_name: PersonName
    email: EmailStr
    position: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    department_id: int = Field(gt=0)
    status: EmployeeStatus = EmployeeStatus.ACTIVE
    hired_at: date


class EmployeeRead(ORMModel):
    about: str
    experience: str
    education: str
    id: int
    first_name: str
    last_name: str
    email: str
    position: str
    department_id: int
    status: EmployeeStatus
    hired_at: date
    department: DepartmentRead


class EmployeePage(BaseModel):
    items: list[EmployeeRead]
    total: int
    page: int
    page_size: int


class SkillWrite(BaseModel):
    name: Name
    category: PersonName
    description: str = Field(default="", max_length=2000)


class SkillRead(ORMModel):
    id: int
    name: str
    category: str
    description: str


class SkillSummary(SkillRead):
    employee_count: int


class AssessmentWrite(BaseModel):
    current_level: int | None = Field(default=None, ge=0, le=5)
    target_level: int = Field(ge=1, le=5)


class CertificateRead(ORMModel):
    id: int
    title: str
    original_name: str
    content_type: str
    size: int
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def utc_created_at(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class AssessmentRead(ORMModel):
    skill: SkillRead
    current_level: int | None
    target_level: int
    state: AssessmentState
    updated_at: datetime
    certificates: list[CertificateRead]


class EmployeeDetail(EmployeeRead):
    skills: list[AssessmentRead]


class ActivityRead(ORMModel):
    actor_username: str
    id: int
    kind: str
    title: str
    detail: str
    employee_id: int | None
    created_at: datetime


class DashboardStats(BaseModel):
    employees: int
    active_employees: int
    probation_employees: int
    leave_employees: int
    departments: int
    skills: int
    assignments: int
    assessed: int
    coverage: int
    gaps: int
    unassessed: int


class SkillMetric(BaseModel):
    id: int
    name: str
    category: str
    assigned: int
    assessed: int
    at_target: int
    coverage: int
    average_level: float | None


class DashboardRead(BaseModel):
    stats: DashboardStats
    departments: list[DepartmentSummary]
    skill_metrics: list[SkillMetric]
    activities: list[ActivityRead]
    recent_employees: list[EmployeeRead]


class MatrixEmployee(EmployeeRead):
    skills: list[AssessmentRead]


class MatrixRead(BaseModel):
    skills: list[SkillRead]
    employees: list[MatrixEmployee]
    total: int
    page: int
    page_size: int
