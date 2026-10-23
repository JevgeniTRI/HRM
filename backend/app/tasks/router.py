from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select

from app.dependencies import DB
from app.models import Employee
from app.permissions import employee_scope
from app.services import tasks as service
from app.tasks.schemas import (
    EffortEstimate,
    EffortRead,
    LearningFormat,
    LearningSource,
    TaskPage,
    TaskRead,
    TaskStatus,
    TaskStatusWrite,
    TaskSummary,
    TaskUpdate,
    TaskWrite,
)

router = APIRouter(prefix="/tasks", tags=["Задачи"])


def task_filters(
    q: Annotated[str, Query(max_length=100)] = "",
    department_id: Annotated[int | None, Query(gt=0)] = None,
    learning_source: LearningSource | None = None,
    learning_format: LearningFormat | None = None,
    is_training: bool | None = None,
) -> dict:
    return {
        "q": q,
        "department_id": department_id,
        "learning_source": learning_source,
        "learning_format": learning_format,
        "is_training": is_training,
    }


Filters = Annotated[dict, Depends(task_filters)]


@router.get("", response_model=TaskPage)
def list_tasks(
    session: DB,
    filters: Filters,
    status: TaskStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return service.list_tasks(session, page=page, page_size=page_size, status=status, **filters)


@router.get("/summary", response_model=TaskSummary)
def summary(session: DB, filters: Filters):
    return service.summarize_tasks(session, **filters)


@router.post("/estimate", response_model=EffortRead)
def estimate(data: EffortEstimate):
    return service.estimate_effort(data)


@router.post("", response_model=TaskRead, status_code=201)
def create_task(data: TaskWrite, session: DB):
    validate_assignment(data, session)
    return service.create_task(session, data)


@router.get("/{task_id}", response_model=TaskRead)
def read_task(task_id: int, session: DB):
    return service.read_task(session, task_id)


@router.put("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, data: TaskUpdate, session: DB):
    current = service.read_task(session, task_id)
    actor = session.info["actor"]
    if actor.role == "employee":
        if data.assignee_id != current.assignee_id or set(data.department_ids) != {
            d.id for d in current.departments
        }:
            raise HTTPException(403, "Исполнителя и отделы назначает руководитель")
    validate_assignment(data, session, existing=actor.role == "employee")
    return service.update_task(session, task_id, data)


def validate_assignment(data: TaskWrite, session, existing=False):
    actor = session.info["actor"]
    if actor.role == "employee" and data.assignee_id != actor.employee_id:
        raise HTTPException(403, "Можно создавать задачи только для себя")
    if (
        not actor.global_access
        and not existing
        and any(d != actor.department_id for d in data.department_ids)
    ):
        raise HTTPException(403, "Можно назначать задачи только своему отделу")
    if (
        actor.role == "manager"
        and data.assignee_id is None
        and data.department_ids != [actor.department_id]
    ):
        raise HTTPException(422, "Выберите исполнителя или свой отдел")
    if data.assignee_id is not None:
        person = session.scalar(
            select(Employee).where(Employee.id == data.assignee_id, employee_scope(session))
        )
        if person is None:
            raise HTTPException(422, "Исполнитель недоступен")


@router.put("/{task_id}/status", response_model=TaskRead)
def change_status(task_id: int, data: TaskStatusWrite, session: DB):
    return service.change_status(session, task_id, data)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, session: DB, version: Annotated[int, Query(ge=1)]):
    service.delete_task(session, task_id, version)
    return Response(status_code=204)
