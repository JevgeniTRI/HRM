import csv
import io

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.errors import ConflictError
from app.models import Department, Employee, EmployeeSkill
from app.permissions import employee_scope
from app.schemas import EmployeeStatus, EmployeeWrite
from app.services.common import commit, escaped_search, record_activity, require_record
from app.storage import remove_files


def employee_query(q: str = "", department_id: int | None = None, status: str | None = None):
    statement = select(Employee)
    if q.strip():
        statement = statement.where(
            Employee.search_text.like(f"%{escaped_search(q)}%", escape="\\")
        )
    if department_id is not None:
        statement = statement.where(Employee.department_id == department_id)
    if status is not None:
        statement = statement.where(Employee.status == status)
    return statement


def employee_values(data: EmployeeWrite) -> dict:
    values = data.model_dump()
    values["email"] = str(data.email).casefold()
    values["search_text"] = " ".join(
        [
            data.first_name,
            data.last_name,
            data.last_name,
            data.first_name,
            data.position,
            values["email"],
        ]
    ).casefold()
    return values


def get_employee_detail(session: Session, employee_id: int) -> Employee:
    employee = session.scalar(
        select(Employee)
        .where(Employee.id == employee_id)
        .options(
            selectinload(Employee.department),
            selectinload(Employee.skills).selectinload(EmployeeSkill.skill),
            selectinload(Employee.skills).selectinload(EmployeeSkill.certificates),
        )
        .execution_options(populate_existing=True)
    )
    if employee is None:
        return require_record(session, Employee, employee_id)
    return employee


def list_employees(
    session: Session,
    q: str = "",
    department_id: int | None = None,
    status: EmployeeStatus | None = None,
    page: int = 1,
    page_size: int = 10,
):
    query = employee_query(q, department_id, status).where(employee_scope(session))
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = session.scalars(
        query.options(selectinload(Employee.department))
        .order_by(Employee.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def csv_cell(value: str) -> str:
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def export_employees(
    session: Session,
    q: str = "",
    department_id: int | None = None,
    status: EmployeeStatus | None = None,
):
    employees = session.scalars(
        employee_query(q, department_id, status)
        .where(employee_scope(session))
        .options(selectinload(Employee.department))
        .order_by(Employee.id)
    ).all()
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        ["Имя", "Фамилия", "Email", "Должность", "Подразделение", "Статус", "Дата приёма"]
    )
    labels = {
        "active": "Работает",
        "probation": "Испытательный срок",
        "leave": "В отпуске",
        "inactive": "Неактивен",
    }
    for employee in employees:
        writer.writerow(
            [
                csv_cell(str(value))
                for value in (
                    employee.first_name,
                    employee.last_name,
                    employee.email,
                    employee.position,
                    employee.department.name,
                    labels[employee.status],
                    employee.hired_at.isoformat(),
                )
            ]
        )
    return output.getvalue().encode("utf-8-sig")


def create_employee(data: EmployeeWrite, session: Session):
    require_record(session, Department, data.department_id)
    employee = Employee(**employee_values(data))
    session.add(employee)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("Сотрудник с таким email уже существует") from exc
    record_activity(
        session,
        "employee",
        "Добавлен сотрудник",
        f"{employee.first_name} {employee.last_name} · {employee.position}",
        employee.id,
    )
    commit(session, "Сотрудник с таким email уже существует")
    return get_employee_detail(session, employee.id)


def update_employee(employee_id: int, data: EmployeeWrite, session: Session):
    employee = require_record(session, Employee, employee_id)
    require_record(session, Department, data.department_id)
    for key, value in employee_values(data).items():
        setattr(employee, key, value)
    record_activity(
        session,
        "employee",
        "Обновлена карточка сотрудника",
        f"{employee.first_name} {employee.last_name}",
        employee.id,
    )
    commit(session, "Сотрудник с таким email уже существует")
    return get_employee_detail(session, employee.id)


def delete_employee(employee_id: int, session: Session):
    employee = require_record(session, Employee, employee_id)
    stored_names = [file.stored_name for item in employee.skills for file in item.certificates]
    record_activity(
        session, "employee", "Удалён сотрудник", f"{employee.first_name} {employee.last_name}"
    )
    session.delete(employee)
    commit(session, "Не удалось удалить сотрудника")
    remove_files(stored_names)
    return None
