from datetime import UTC, date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.services.assessment_rules import AssessmentState, assessment_state


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
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    position: Mapped[str] = mapped_column(String(120))
    about: Mapped[str] = mapped_column(Text, default="")
    experience: Mapped[str] = mapped_column(Text, default="")
    education: Mapped[str] = mapped_column(Text, default="")
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


class Skill(Base):
    __tablename__ = "skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    name_key: Mapped[str] = mapped_column(String(300), unique=True)
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")


class EmployeeSkill(Base):
    __tablename__ = "employee_skills"
    __table_args__ = (
        UniqueConstraint("employee_id", "skill_id"),
        CheckConstraint("current_level IS NULL OR current_level BETWEEN 0 AND 5"),
        CheckConstraint("target_level BETWEEN 1 AND 5"),
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
    __table_args__ = (CheckConstraint("size > 0 AND size <= 10485760"),)
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
