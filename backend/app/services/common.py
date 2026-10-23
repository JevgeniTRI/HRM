from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.database import Base
from app.errors import ConflictError, NotFoundError
from app.models import Activity


def require_record[Model: Base](session: Session, model: type[Model], record_id: int) -> Model:
    record = session.get(model, record_id)
    if record is None:
        raise NotFoundError("Запись не найдена")
    return record


def commit(session: Session, conflict_message: str) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError(conflict_message) from exc
    except StaleDataError as exc:
        session.rollback()
        raise ConflictError("Запись уже изменена. Обновите данные и повторите действие") from exc


def record_activity(
    session: Session, kind: str, title: str, detail: str = "", employee_id: int | None = None
) -> None:
    session.add(
        Activity(
            kind=kind,
            title=title,
            detail=detail[:300],
            employee_id=employee_id,
            actor_username=session.info.get("actor_username", "Система"),
        )
    )


def escaped_search(value: str) -> str:
    return value.strip().casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
