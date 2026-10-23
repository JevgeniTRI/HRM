from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response

from app.dependencies import DB
from app.schemas import EmployeeDetail, EmployeePage, EmployeeStatus, EmployeeWrite
from app.services import personnel

router = APIRouter(prefix="/employees", tags=["Сотрудники"])


@router.get("", response_model=EmployeePage)
def list_employees(
    session: DB,
    q: Annotated[str, Query(max_length=100)] = "",
    department_id: int | None = None,
    status: EmployeeStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
):
    return personnel.list_employees(session, q, department_id, status, page, page_size)


@router.get("/export")
def export_employees(
    session: DB,
    q: Annotated[str, Query(max_length=100)] = "",
    department_id: int | None = None,
    status: EmployeeStatus | None = None,
):
    return Response(
        content=personnel.export_employees(session, q, department_id, status),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="employees.csv"'},
    )


@router.post("", response_model=EmployeeDetail, status_code=201)
def create_employee(data: EmployeeWrite, session: DB):
    return personnel.create_employee(data, session)


@router.get("/{employee_id}", response_model=EmployeeDetail)
def read_employee(employee_id: int, session: DB):
    return personnel.get_employee_detail(session, employee_id)


@router.put("/{employee_id}", response_model=EmployeeDetail)
def update_employee(employee_id: int, data: EmployeeWrite, session: DB):
    actor = session.info["actor"]
    if not actor.global_access:
        current = personnel.get_employee_detail(session, employee_id)
        if data.department_id != current.department_id:
            raise HTTPException(
                403,
                "Перевод между отделами доступен только администратору "
                "и пользователю с повышенными правами",
            )
        if actor.role == "employee" and any(
            getattr(current, field) != getattr(data, field)
            for field in ("position", "status", "hired_at")
        ):
            raise HTTPException(403, "Должность, статус и дату приёма изменяет руководитель")
    return personnel.update_employee(employee_id, data, session)


@router.delete("/{employee_id}", status_code=204)
def delete_employee(employee_id: int, session: DB):
    personnel.delete_employee(employee_id, session)
    return Response(status_code=204)
