from datetime import date

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.errors import ConflictError, NotFoundError
from app.models import Department, utc_now
from app.permissions import task_scope
from app.services.common import commit, escaped_search, record_activity, require_record
from app.services.task_rules import from_hundredths, person_hours, to_hundredths
from app.tasks.models import Task
from app.tasks.schemas import EffortEstimate, TaskStatus, TaskStatusWrite, TaskUpdate, TaskWrite


def estimate_effort(data: EffortEstimate) -> dict:
    return {
        "person_hours": person_hours(to_hundredths(data.duration_hours), data.participant_count)
    }


def task_query(
    q: str = "",
    department_id: int | None = None,
    learning_source: str | None = None,
    learning_format: str | None = None,
    is_training: bool | None = None,
    status: str | None = None,
):
    query = select(Task)
    if q.strip():
        query = query.where(Task.search_text.like(f"%{escaped_search(q)}%", escape="\\"))
    if department_id is not None:
        query = query.where(Task.departments.any(Department.id == department_id))
    if learning_source is not None:
        query = query.where(Task.learning_source == learning_source)
    if learning_format is not None:
        query = query.where(Task.learning_format == learning_format)
    if is_training is not None:
        query = query.where(
            Task.learning_source.is_not(None) if is_training else Task.learning_source.is_(None)
        )
    if status is not None:
        query = query.where(Task.status == status)
    return query


def list_tasks(session: Session, *, page: int, page_size: int, **filters):
    query = task_query(**filters).where(task_scope(session))
    return task_page(session, query, page, page_size, Task.updated_at.desc(), Task.id.desc())


def calendar_tasks(
    session: Session, *, from_on: date, to_on: date, page: int, page_size: int, **filters
):
    filters["is_training"] = True
    query = task_query(**filters).where(
        task_scope(session),
        or_(
            Task.start_on.is_(None),
            and_(Task.start_on <= to_on, Task.end_on >= from_on),
        ),
    )
    return task_page(session, query, page, page_size, Task.start_on.asc().nulls_last(), Task.id)


def task_page(session: Session, query, page: int, page_size: int, *ordering):
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = session.scalars(
        query.options(selectinload(Task.departments), selectinload(Task.assignee))
        .order_by(*ordering)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def summarize_tasks(session: Session, **filters):
    tasks = task_query(**filters).where(task_scope(session)).subquery()
    counts = dict(
        session.execute(select(tasks.c.status, func.count()).group_by(tasks.c.status)).all()
    )
    hours_hundredths = (
        session.scalar(select(func.sum(tasks.c.duration_hundredths * tasks.c.participant_count)))
        or 0
    )
    training_count = (
        session.scalar(
            select(func.count()).select_from(tasks).where(tasks.c.learning_source.is_not(None))
        )
        or 0
    )
    unestimated = (
        session.scalar(
            select(func.count())
            .select_from(tasks)
            .where(tasks.c.learning_source.is_not(None), tasks.c.duration_hundredths.is_(None))
        )
        or 0
    )
    without_cost = (
        session.scalar(select(func.count()).select_from(tasks).where(tasks.c.cost_minor.is_(None)))
        or 0
    )
    costs = session.execute(
        select(tasks.c.currency, func.sum(tasks.c.cost_minor))
        .where(tasks.c.currency.is_not(None))
        .group_by(tasks.c.currency)
        .order_by(tasks.c.currency)
    ).all()
    return {
        "total": sum(counts.values()),
        "status_counts": {status: counts.get(status, 0) for status in TaskStatus},
        "person_hours": from_hundredths(hours_hundredths),
        "training_count": training_count,
        "unestimated_training_count": unestimated,
        "costs": [
            {"currency": currency, "amount": from_hundredths(total)} for currency, total in costs
        ],
        "without_cost_count": without_cost,
    }


def task_values(data: TaskWrite) -> dict:
    values = data.model_dump(exclude={"department_ids", "duration_hours", "cost", "version"})
    values["duration_hundredths"] = to_hundredths(data.duration_hours)
    values["cost_minor"] = to_hundredths(data.cost)
    values["search_text"] = f"{data.title} {data.description}".casefold()
    return values


def selected_departments(session: Session, ids: list[int]) -> list[Department]:
    departments = session.scalars(
        select(Department).where(Department.id.in_(ids)).order_by(Department.name_key)
    ).all()
    if len(departments) != len(ids):
        raise NotFoundError("Одно из подразделений не найдено")
    return list(departments)


def read_task(session: Session, task_id: int) -> Task:
    task = session.scalar(
        select(Task)
        .where(Task.id == task_id)
        .options(selectinload(Task.departments), selectinload(Task.assignee))
    )
    if task is None:
        raise NotFoundError("Задача не найдена")
    return task


def check_version(task: Task, expected: int) -> None:
    if task.version != expected:
        raise ConflictError("Задача уже изменена. Обновите карточку и повторите действие")


def create_task(session: Session, data: TaskWrite) -> Task:
    departments = selected_departments(session, data.department_ids)
    task = Task(**task_values(data), departments=departments)
    session.add(task)
    record_activity(session, "task", "Добавлена задача", data.title)
    commit(session, "Не удалось создать задачу: связанные данные изменились")
    return task


def update_task(session: Session, task_id: int, data: TaskUpdate) -> Task:
    task = read_task(session, task_id)
    check_version(task, data.version)
    departments = selected_departments(session, data.department_ids)
    for key, value in task_values(data).items():
        setattr(task, key, value)
    task.departments = departments
    task.updated_at = utc_now()
    record_activity(session, "task", "Обновлена задача", task.title)
    commit(session, "Не удалось обновить задачу: связанные данные изменились")
    session.expire(task, ["assignee"])
    return task


def change_status(session: Session, task_id: int, data: TaskStatusWrite) -> Task:
    task = read_task(session, task_id)
    check_version(task, data.version)
    if task.status != data.status:
        labels = {"todo": "To Do", "in_progress": "In Progress", "done": "Done"}
        task.status = data.status
        task.updated_at = utc_now()
        record_activity(
            session, "task", "Изменён статус задачи", f"{task.title} · {labels[data.status]}"
        )
        commit(session, "Не удалось изменить статус задачи")
    return task


def delete_task(session: Session, task_id: int, version: int) -> None:
    task = require_record(session, Task, task_id)
    check_version(task, version)
    record_activity(session, "task", "Удалена задача", task.title)
    session.delete(task)
    commit(session, "Не удалось удалить задачу")
