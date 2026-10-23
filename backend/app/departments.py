from fastapi import APIRouter, Response

from app.dependencies import DB
from app.schemas import DepartmentRead, DepartmentSummary, DepartmentWrite
from app.services import departments

router = APIRouter(prefix="/departments", tags=["Подразделения"])


@router.get("", response_model=list[DepartmentSummary])
def list_departments(session: DB):
    return departments.department_summaries(session)


@router.post("", response_model=DepartmentRead, status_code=201)
def create_department(data: DepartmentWrite, session: DB):
    return departments.create_department(data, session)


@router.put("/{department_id}", response_model=DepartmentRead)
def update_department(department_id: int, data: DepartmentWrite, session: DB):
    return departments.update_department(department_id, data, session)


@router.delete("/{department_id}", status_code=204)
def delete_department(department_id: int, session: DB):
    departments.delete_department(department_id, session)
    return Response(status_code=204)
