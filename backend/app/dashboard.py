from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import DB
from app.schemas import DashboardRead, EmployeeStatus, MatrixRead
from app.services import overview

router = APIRouter(tags=["Обзор"])


@router.get("/dashboard", response_model=DashboardRead)
def read_dashboard(session: DB):
    return overview.read_dashboard(session)


@router.get("/matrix", response_model=MatrixRead)
def read_matrix(
    session: DB,
    q: Annotated[str, Query(max_length=100)] = "",
    department_id: int | None = None,
    status: EmployeeStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return overview.read_matrix(session, q, department_id, status, page, page_size)
