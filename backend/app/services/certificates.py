from collections.abc import Iterable
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import NotFoundError, PayloadTooLargeError, ValidationError
from app.models import Certificate, Employee, EmployeeSkill
from app.services.common import commit, record_activity, require_record
from app.storage import certificate_path, remove_files

MAX_FILE_SIZE = 15 * 1024 * 1024
FILE_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def require_assessment(session: Session, employee_id: int, skill_id: int) -> EmployeeSkill:
    require_record(session, Employee, employee_id)
    assessment = session.scalar(
        select(EmployeeSkill).where(
            EmployeeSkill.employee_id == employee_id, EmployeeSkill.skill_id == skill_id
        )
    )
    if assessment is None:
        raise NotFoundError("Сначала добавьте навык сотруднику")
    return assessment


def require_certificate(
    session: Session, employee_id: int, skill_id: int, certificate_id: int
) -> Certificate:
    assessment = require_assessment(session, employee_id, skill_id)
    certificate = session.scalar(
        select(Certificate).where(
            Certificate.id == certificate_id, Certificate.employee_skill_id == assessment.id
        )
    )
    if certificate is None:
        raise NotFoundError("Сертификат не найден")
    return certificate


def list_certificates(session: Session, employee_id: int, skill_id: int) -> Iterable[Certificate]:
    return require_assessment(session, employee_id, skill_id).certificates


def read_certificate_file(
    session: Session, employee_id: int, skill_id: int, certificate_id: int
) -> tuple[Certificate, Path]:
    certificate = require_certificate(session, employee_id, skill_id, certificate_id)
    path = certificate_path(certificate.stored_name)
    if not path.is_file():
        raise NotFoundError("Файл сертификата не найден")
    return certificate, path


def valid_signature(extension: str, header: bytes) -> bool:
    if extension == ".pdf":
        return header.startswith(b"%PDF-")
    if extension == ".png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in (".jpg", ".jpeg"):
        return header.startswith(b"\xff\xd8\xff")
    return header.startswith(b"RIFF") and header[8:12] == b"WEBP"


def upload_certificate(
    session: Session,
    employee_id: int,
    skill_id: int,
    stream: BinaryIO,
    filename: str | None,
    title: str,
) -> Certificate:
    assessment = require_assessment(session, employee_id, skill_id)
    original_name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not original_name or len(original_name) > 255 or any(ord(c) < 32 for c in original_name):
        raise ValidationError("Недопустимое имя файла")
    title = title.strip() or original_name[:160]
    if len(title) > 160:
        raise ValidationError("Название сертификата должно быть не длиннее 160 символов")
    extension = Path(original_name).suffix.lower()
    if extension not in FILE_TYPES:
        raise ValidationError("Допустимы файлы PDF, PNG, JPG и WebP")
    header = stream.read(12)
    if not valid_signature(extension, header):
        raise ValidationError("Содержимое файла не соответствует формату сертификата")
    stored_name = f"{uuid4().hex}{extension}"
    path = certificate_path(stored_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    try:
        with path.open("xb") as output:
            chunk = header
            while chunk:
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise PayloadTooLargeError("Размер сертификата не должен превышать 15 МБ")
                output.write(chunk)
                chunk = stream.read(64 * 1024)
        certificate = Certificate(
            employee_skill_id=assessment.id,
            title=title,
            original_name=original_name,
            stored_name=stored_name,
            content_type=FILE_TYPES[extension],
            size=size,
        )
        session.add(certificate)
        record_activity(
            session,
            "certificate",
            "Добавлен сертификат",
            f"{assessment.skill.name} · {title}",
            employee_id,
        )
        commit(session, "Не удалось сохранить сертификат. Обновите страницу")
    except Exception:
        session.rollback()
        path.unlink(missing_ok=True)
        raise
    return certificate


def delete_certificate(session: Session, employee_id: int, skill_id: int, certificate_id: int):
    certificate = require_certificate(session, employee_id, skill_id, certificate_id)
    stored_name = certificate.stored_name
    record_activity(session, "certificate", "Удалён сертификат", certificate.title, employee_id)
    session.delete(certificate)
    commit(session, "Не удалось удалить сертификат")
    remove_files([stored_name])
