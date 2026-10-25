"""Data scopes shared by HTTP guards and domain queries."""

from dataclasses import dataclass

from sqlalchemy import false, select, true

from app.models import Employee
from app.tasks.models import Task


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
        return Employee.id.in_(reporting_tree_ids(actor.employee_id, actor.department_id))
    return Employee.id == actor.employee_id


def reporting_tree_ids(employee_id, department_id):
    # UNION also terminates safely if invalid legacy data ever contains a cycle.
    tree = (
        select(Employee.id)
        .where(Employee.id == employee_id, Employee.department_id == department_id)
        .cte(recursive=True)
    )
    tree = tree.union(
        select(Employee.id)
        .join(tree, Employee.manager_id == tree.c.id)
        .where(Employee.department_id == department_id)
    )
    return select(tree.c.id)


def visible_employee_ids(session):
    return select(Employee.id).where(employee_scope(session))


def department_scope(session, column):
    actor = session.info.get("actor")
    if actor is None or actor.global_access:
        return true()
    if actor.role == "manager":
        return column.in_(select(Employee.department_id).where(employee_scope(session)))
    return column == actor.department_id if actor.department_id is not None else false()


def task_scope(session):
    actor = session.info.get("actor")
    if actor is None or actor.global_access:
        return true()
    return Task.assignee_id.in_(visible_employee_ids(session))
