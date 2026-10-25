from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.services.assessment_rules import (
    AssessmentState,
    assessment_state,
    default_level_names,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    name_key: Mapped[str] = mapped_column(String(300), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'probation', 'leave', 'inactive')", name="ck_employees_status"
        ),
        CheckConstraint(
            "manager_id IS NULL OR manager_id != id", name="ck_employees_not_own_manager"
        ),
        CheckConstraint(
            "(photo_stored_name IS NULL AND photo_content_type IS NULL AND photo_size IS NULL) OR "
            "(photo_stored_name IS NOT NULL AND photo_content_type IS NOT NULL "
            "AND photo_size > 0 AND photo_size <= 5242880)",
            name="ck_employees_profile_photo",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    position: Mapped[str] = mapped_column(String(120))
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT", use_alter=True, name="fk_employees_team"),
        index=True,
    )
    team: Mapped["Team | None"] = relationship(foreign_keys=[team_id])
    is_manager: Mapped[bool] = mapped_column(default=False, server_default="0")
    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), index=True
    )
    manager: Mapped["Employee | None"] = relationship(
        remote_side="Employee.id", back_populates="direct_reports", foreign_keys=[manager_id]
    )
    direct_reports: Mapped[list["Employee"]] = relationship(
        back_populates="manager",
        passive_deletes="all",
        foreign_keys=[manager_id],
        order_by="Employee.last_name, Employee.first_name, Employee.id",
    )
    about: Mapped[str] = mapped_column(Text, default="")
    experience: Mapped[str] = mapped_column(Text, default="")
    education: Mapped[str] = mapped_column(Text, default="")
    photo_stored_name: Mapped[str | None] = mapped_column(String(50), unique=True)
    photo_content_type: Mapped[str | None] = mapped_column(String(30))
    photo_size: Mapped[int | None]
    photo_version: Mapped[int] = mapped_column(default=0, server_default="0")
    search_text: Mapped[str] = mapped_column(String(720))
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active")
    hired_at: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    department: Mapped[Department] = relationship()
    skills: Mapped[list["EmployeeSkill"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def organization_role(self) -> str:
        if not self.is_manager:
            return "employee"
        return "head" if self.manager_id is None else "intermediate"

    @property
    def has_photo(self) -> bool:
        return self.photo_stored_name is not None


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), index=True
    )
    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), unique=True
    )
    supervisor_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT")
    )
    version: Mapped[int] = mapped_column(default=1, server_default="1")
    department: Mapped[Department] = relationship()
    manager: Mapped[Employee | None] = relationship(foreign_keys=[manager_id])
    supervisor: Mapped[Employee | None] = relationship(foreign_keys=[supervisor_id])


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (
        CheckConstraint(
            "scale_min >= 0 AND scale_min <= scale_max AND "
            "((scale_type = 'numeric' AND scale_max <= 10) OR "
            "(scale_type = 'letter' AND scale_max <= 25))",
            name="ck_skills_scale",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    name_key: Mapped[str] = mapped_column(String(300), unique=True)
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    scale_type: Mapped[str] = mapped_column(String(10), default="numeric", server_default="numeric")
    scale_min: Mapped[int] = mapped_column(default=0, server_default="0")
    scale_max: Mapped[int] = mapped_column(default=5, server_default="5")
    level_descriptions: Mapped[dict[str, str]] = mapped_column(
        JSON, default=dict, server_default="{}"
    )
    level_names: Mapped[dict[str, str]] = mapped_column(
        JSON, default=default_level_names, server_default="{}"
    )

    @property
    def scale(self) -> dict:
        return {
            "type": self.scale_type,
            "min": self.scale_min,
            "max": self.scale_max,
            "descriptions": self.level_descriptions,
            "names": self.level_names,
        }


class EmployeeSkill(Base):
    __tablename__ = "employee_skills"
    __table_args__ = (
        UniqueConstraint("employee_id", "skill_id"),
        CheckConstraint(
            "current_level IS NULL OR current_level BETWEEN 0 AND 25",
            name="ck_employee_skills_current_level",
        ),
        CheckConstraint("target_level BETWEEN 0 AND 25", name="ck_employee_skills_target_level"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="RESTRICT"), index=True)
    current_level: Mapped[int | None]
    target_level: Mapped[int] = mapped_column(default=3)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    skill: Mapped[Skill] = relationship()
    certificates: Mapped[list["Certificate"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="Certificate.id.desc()"
    )

    @property
    def state(self) -> AssessmentState:
        return assessment_state(self.current_level, self.target_level)


class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (
        CheckConstraint("size > 0 AND size <= 15728640", name="ck_certificates_size"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_skill_id: Mapped[int] = mapped_column(
        ForeignKey("employee_skills.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(160))
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(50), unique=True)
    content_type: Mapped[str] = mapped_column(String(30))
    size: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Activity(Base):
    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_username: Mapped[str] = mapped_column(String(80), default="Система")
    kind: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(250))
    detail: Mapped[str] = mapped_column(String(300), default="")
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'power_user', 'manager', 'employee')", name="ck_accounts_role"
        ),
        CheckConstraint("role = 'admin' OR employee_id IS NOT NULL", name="ck_accounts_employee"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(20))
    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), unique=True
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    employee: Mapped[Employee | None] = relationship()


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ImportIdentity(Base):
    __tablename__ = "import_identities"
    __table_args__ = (
        UniqueConstraint("source", "entity", "external_id"),
        UniqueConstraint("source", "department_id"),
        UniqueConstraint("source", "employee_id"),
        UniqueConstraint("source", "team_id"),
        UniqueConstraint("source", "skill_id"),
        CheckConstraint(
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
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(40))
    entity: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str] = mapped_column(String(120))
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE")
    )
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))


class IntegrationKey(Base):
    __tablename__ = "integration_keys"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(40))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    prefix: Mapped[str] = mapped_column(String(20))
    entities: Mapped[list[str]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ImportRun(Base):
    __tablename__ = "import_runs"
    __table_args__ = (UniqueConstraint("source", "request_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(40))
    request_id: Mapped[str] = mapped_column(String(120))
    channel: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(10))
    actor_username: Mapped[str] = mapped_column(String(80))
    payload_hash: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
