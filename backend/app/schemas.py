from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

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
    has_photo: bool
    photo_version: int
    team_id: int | None
    is_manager: bool
    manager_id: int | None
    organization_role: Literal["head", "intermediate", "employee"]
    department_id: int
    status: EmployeeStatus
    hired_at: date
    department: DepartmentRead


class EmployeePage(BaseModel):
    items: list[EmployeeRead]
    total: int
    page: int
    page_size: int


class SkillScale(BaseModel):
    type: Literal["numeric", "letter"] = "numeric"
    min: int = Field(default=0, ge=0, le=25, strict=True)
    max: int = Field(default=5, ge=0, le=25, strict=True)
    descriptions: dict[
        str, Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
    ] = Field(default_factory=dict, max_length=26)
    names: dict[str, Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]] = (
        Field(default_factory=dict, max_length=26)
    )

    @model_validator(mode="after")
    def validate_scale(self):
        if self.min > self.max:
            raise ValueError("Начало диапазона не может быть больше конца")
        if self.type == "numeric" and self.max > 10:
            raise ValueError("Числовая шкала должна находиться в пределах 0–10")
        allowed = {str(level) for level in range(self.min, self.max + 1)}
        if not self.descriptions.keys() <= allowed:
            raise ValueError("Описание можно задать только для уровней выбранного диапазона")
        if not self.names.keys() <= allowed:
            raise ValueError("Название можно задать только для уровней выбранного диапазона")
        return self


class SkillWrite(BaseModel):
    name: Name
    category: PersonName
    description: str = Field(default="", max_length=2000)
    scale: SkillScale | None = None


class SkillRead(ORMModel):
    id: int
    name: str
    category: str
    description: str
    scale: SkillScale


class SkillSummary(SkillRead):
    employee_count: int


class AssessmentWrite(BaseModel):
    current_level: int | None = Field(default=None, ge=0, le=25, strict=True)
    target_level: int = Field(ge=0, le=25, strict=True)


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


class EmployeeReference(ORMModel):
    id: int
    first_name: str
    last_name: str
    position: str
    is_manager: bool
    organization_role: Literal["head", "intermediate", "employee"]
    department: DepartmentRead


class OrganizationWrite(BaseModel):
    kind: Literal["head", "intermediate", "employee"]
    manager_id: int | None = Field(default=None, gt=0, strict=True)
    report_ids: list[Annotated[int, Field(gt=0, strict=True)]] | None = Field(
        default=None, max_length=1000
    )


class EmployeeDetail(EmployeeRead):
    skills: list[AssessmentRead]
    manager: EmployeeReference | None
    direct_reports: list[EmployeeReference]
    team: "TeamReference | None"


class TeamReference(ORMModel):
    id: int
    code: str
    name: str


class TeamWrite(BaseModel):
    code: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            to_upper=True,
            min_length=1,
            max_length=40,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ]
    name: Name
    department_id: int = Field(gt=0)
    manager_id: int | None = Field(default=None, gt=0)
    supervisor_id: int | None = Field(default=None, gt=0)


class TeamRead(TeamReference):
    department: DepartmentRead
    manager: EmployeeReference | None
    supervisor: EmployeeReference | None
    member_count: int
    version: int


class TeamAssignment(BaseModel):
    employee_ids: list[Annotated[int, Field(gt=0, strict=True)]] = Field(
        min_length=1, max_length=10000
    )
    version: int = Field(ge=1)


class TeamReplacement(BaseModel):
    manager_id: int = Field(gt=0)
    version: int = Field(ge=1)


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
    scale: SkillScale


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
