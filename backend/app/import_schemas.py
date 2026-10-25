from datetime import UTC, date, datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_serializer,
    model_validator,
)

from app.schemas import EmployeeStatus, Name, PersonName

Entity = Literal["departments", "employees", "teams", "skills"]
Source = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=1,
        max_length=40,
        pattern=r"^[a-zA-Z0-9_.-]+$",
    ),
]
ExternalId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class ImportRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_id: ExternalId


class DepartmentImport(ImportRecord):
    name: Name | None = None
    description: str | None = Field(default=None, max_length=2000)


class EmployeeImport(ImportRecord):
    first_name: PersonName | None = None
    last_name: PersonName | None = None
    email: EmailStr | None = None
    position: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
        | None
    ) = None
    department_external_id: ExternalId | None = None
    team_external_id: ExternalId | None = None
    manager_external_id: ExternalId | None = None
    status: EmployeeStatus | None = None
    hired_at: date | None = None
    about: str | None = Field(default=None, max_length=5000)
    experience: str | None = Field(default=None, max_length=10000)
    education: str | None = Field(default=None, max_length=5000)


class TeamImport(ImportRecord):
    name: Name | None = None
    code: (
        Annotated[
            str,
            StringConstraints(
                strip_whitespace=True,
                to_upper=True,
                min_length=1,
                max_length=40,
                pattern=r"^[A-Za-z0-9_-]+$",
            ),
        ]
        | None
    ) = None
    department_external_id: ExternalId | None = None
    manager_external_id: ExternalId | None = None
    supervisor_external_id: ExternalId | None = None


class SkillImport(ImportRecord):
    name: Name | None = None
    category: PersonName | None = None
    description: str | None = Field(default=None, max_length=2000)


class ImportBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    departments: list[DepartmentImport] = Field(default_factory=list, max_length=10000)
    employees: list[EmployeeImport] = Field(default_factory=list, max_length=10000)
    teams: list[TeamImport] = Field(default_factory=list, max_length=10000)
    skills: list[SkillImport] = Field(default_factory=list, max_length=10000)

    @model_validator(mode="after")
    def validate_batch(self):
        total = sum(
            len(getattr(self, entity)) for entity in ("departments", "employees", "teams", "skills")
        )
        if not 1 <= total <= 10000:
            raise ValueError("Пакет должен содержать от 1 до 10 000 записей")
        for entity in ("departments", "employees", "teams", "skills"):
            ids = [record.external_id for record in getattr(self, entity)]
            if len(ids) != len(set(ids)):
                raise ValueError(f"Повторяются external_id в {entity}")
        return self


class IntegrationRequest(ImportBatch):
    request_id: ExternalId


class IntegrationKeyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    source: Source
    entities: list[Entity] = Field(min_length=1, max_length=4)
    expires_at: datetime | None = None


class IntegrationKeyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    source: str
    prefix: str
    entities: list[Entity]
    is_active: bool
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None

    @field_serializer("created_at", "expires_at", "last_used_at")
    def serialize_time(self, value):
        return value.replace(tzinfo=UTC).isoformat() if value else None
