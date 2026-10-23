"""Data scopes shared by HTTP guards and domain queries."""

from dataclasses import dataclass

from sqlalchemy import and_, false, or_, select, true

from app.models import Employee
from app.tasks.models import Task, task_departments


@dataclass(frozen=True)
class Principal:
    id: int
    role: str
    employee_id: int | None
    department_id: int | None

    @property
    def global_access(self):
        return self.role in {"admin", "power_user"}


def employee_scope(session):
    actor = session.info.get("actor")
    if actor is None or actor.global_access:
        return true()
    if actor.role == "manager":
        return Employee.department_id == actor.department_id
    return Employee.id == actor.employee_id


def visible_employee_ids(session):
    return select(Employee.id).where(employee_scope(session))


def department_scope(session, column):
    actor = session.info.get("actor")
    if actor is None or actor.global_access:
        return true()
    return column == actor.department_id if actor.department_id is not None else false()


def task_scope(session):
    actor = session.info.get("actor")
    if actor is None or actor.global_access:
        return true()
    if actor.role == "employee":
        return Task.assignee_id == actor.employee_id
    # Shared tasks spanning other departments remain under global management.
    own_department = select(task_departments.c.task_id).where(
        task_departments.c.department_id == actor.department_id
    )
    other_departments = select(task_departments.c.task_id).where(
        task_departments.c.department_id != actor.department_id
    )
    return and_(
        ~Task.id.in_(other_departments),
        or_(
            Task.assignee_id.in_(visible_employee_ids(session)),
            and_(Task.assignee_id.is_(None), Task.id.in_(own_department)),
        ),
    )
