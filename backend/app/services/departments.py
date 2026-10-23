from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import ConflictError
from app.models import Account, Department, Employee
from app.permissions import department_scope, employee_scope
from app.schemas import DepartmentManager, DepartmentRead, DepartmentSummary, DepartmentWrite
from app.services.common import commit, record_activity, require_record
from app.tasks.models import task_departments


def department_summaries(session) -> list[DepartmentSummary]:
    rows = session.execute(
        select(Department, func.count(Employee.id))
        .outerjoin(Employee, (Employee.department_id == Department.id) & employee_scope(session))
        .where(department_scope(session, Department.id))
        .group_by(Department.id)
        .order_by(Department.name_key)
    ).all()
    managers_by_department: dict[int, list[DepartmentManager]] = {}
    if rows:
        managers = session.execute(
            select(Employee.id, Employee.first_name, Employee.last_name, Employee.department_id)
            .join(Account, Account.employee_id == Employee.id)
            .where(
                Account.role == "manager",
                Account.is_active.is_(True),
                Employee.department_id.in_([department.id for department, _ in rows]),
                employee_scope(session),
            )
            .order_by(Employee.last_name, Employee.first_name, Employee.id)
        ).all()
        for manager in managers:
            managers_by_department.setdefault(manager.department_id, []).append(
                DepartmentManager(id=manager.id, name=f"{manager.first_name} {manager.last_name}")
            )
    return [
        DepartmentSummary(
            **DepartmentRead.model_validate(dept).model_dump(),
            employee_count=count,
            managers=managers_by_department.get(dept.id, []),
        )
        for dept, count in rows
    ]


def create_department(data: DepartmentWrite, session: Session):
    department = Department(**data.model_dump(), name_key=data.name.casefold())
    session.add(department)
    record_activity(session, "department", "Добавлено подразделение", data.name)
    commit(session, "Подразделение с таким названием уже существует")
    return department


def update_department(department_id: int, data: DepartmentWrite, session: Session):
    department = require_record(session, Department, department_id)
    department.name, department.description = data.name, data.description
    department.name_key = data.name.casefold()
    record_activity(session, "department", "Обновлено подразделение", data.name)
    commit(session, "Подразделение с таким названием уже существует")
    return department


def delete_department(department_id: int, session: Session):
    department = require_record(session, Department, department_id)
    if session.scalar(
        select(task_departments.c.task_id)
        .where(task_departments.c.department_id == department_id)
        .limit(1)
    ):
        raise ConflictError(
            "Подразделение используется в задачах. Сначала измените их подразделения"
        )
    if session.scalar(select(Employee.id).where(Employee.department_id == department_id).limit(1)):
        raise ConflictError("Сначала переведите сотрудников в другое подразделение")
    record_activity(session, "department", "Удалено подразделение", department.name)
    session.delete(department)
    commit(session, "В подразделении есть сотрудники")
    return None
