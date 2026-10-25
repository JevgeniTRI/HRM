from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from sqlalchemy.orm import Session

from app.errors import ForbiddenError, NotFoundError, PayloadTooLargeError, ValidationError
from app.models import Employee
from app.services.common import commit, record_activity, require_record
from app.storage import profile_photo_path, remove_profile_photo

MAX_PHOTO_SIZE = 5 * 1024 * 1024
PHOTO_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def valid_signature(extension: str, header: bytes) -> bool:
    if extension == ".png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {".jpg", ".jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    return header.startswith(b"RIFF") and header[8:12] == b"WEBP"


def require_photo_owner(session: Session, employee_id: int) -> Employee:
    employee = require_record(session, Employee, employee_id)
    actor = session.info["actor"]
    if not actor.global_access and actor.employee_id != employee_id:
        raise ForbiddenError("Изменять фотографию может только владелец карточки")
    return employee


def read_photo(session: Session, employee_id: int) -> tuple[Employee, Path]:
    employee = require_record(session, Employee, employee_id)
    if not employee.photo_stored_name:
        raise NotFoundError("Фотография профиля не добавлена")
    path = profile_photo_path(employee.photo_stored_name)
    if not path.is_file():
        raise NotFoundError("Файл фотографии профиля не найден")
    return employee, path


def upload_photo(
    session: Session,
    employee_id: int,
    stream: BinaryIO,
    filename: str | None,
) -> None:
    employee = require_photo_owner(session, employee_id)
    original_name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not original_name or len(original_name) > 255 or any(ord(c) < 32 for c in original_name):
        raise ValidationError("Недопустимое имя файла")
    extension = Path(original_name).suffix.lower()
    if extension not in PHOTO_TYPES:
        raise ValidationError("Допустимы фотографии PNG, JPG и WebP")
    header = stream.read(12)
    if not valid_signature(extension, header):
        raise ValidationError("Содержимое файла не соответствует формату фотографии")
    stored_name = f"{uuid4().hex}{extension}"
    path = profile_photo_path(stored_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    old_name = employee.photo_stored_name
    try:
        with path.open("xb") as output:
            chunk = header
            while chunk:
                size += len(chunk)
                if size > MAX_PHOTO_SIZE:
                    raise PayloadTooLargeError("Размер фотографии не должен превышать 5 МБ")
                output.write(chunk)
                chunk = stream.read(64 * 1024)
        employee.photo_stored_name = stored_name
        employee.photo_content_type = PHOTO_TYPES[extension]
        employee.photo_size = size
        employee.photo_version += 1
        record_activity(
            session,
            "employee",
            "Обновлена фотография профиля",
            f"{employee.first_name} {employee.last_name}",
            employee.id,
        )
        commit(session, "Не удалось сохранить фотографию профиля")
    except Exception:
        session.rollback()
        path.unlink(missing_ok=True)
        raise
    remove_profile_photo(old_name)


def delete_photo(session: Session, employee_id: int) -> None:
    employee = require_photo_owner(session, employee_id)
    old_name = employee.photo_stored_name
    if not old_name:
        raise NotFoundError("Фотография профиля не добавлена")
    employee.photo_stored_name = None
    employee.photo_content_type = None
    employee.photo_size = None
    employee.photo_version += 1
    record_activity(
        session,
        "employee",
        "Удалена фотография профиля",
        f"{employee.first_name} {employee.last_name}",
        employee.id,
    )
    commit(session, "Не удалось удалить фотографию профиля")
    remove_profile_photo(old_name)
