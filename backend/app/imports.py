import secrets
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile
from pydantic import TypeAdapter
from sqlalchemy import select

from app.auth import AdminAccount, token_hash
from app.dependencies import DB
from app.import_schemas import ExternalId, IntegrationKeyCreate, IntegrationKeyRead, Source
from app.models import ImportRun, IntegrationKey
from app.services import data_import, import_files
from app.teams import global_only, read_file

router = APIRouter(prefix="/imports", tags=["Импорт и интеграции"])


@router.get("/template/{kind}")
def template(kind: Literal["csv", "xlsx"], session: DB):
    global_only(session)
    return Response(
        content=import_files.template(kind),
        media_type="text/csv; charset=utf-8"
        if kind == "csv"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="hrm-import-template.{kind}"'},
    )


@router.get("/example")
def example(session: DB):
    global_only(session)
    return import_files.EXAMPLE


@router.post("/preview")
async def preview(
    session: DB, file: Annotated[UploadFile, File()], source: Annotated[Source, Form()] = "manual"
):
    global_only(session)
    try:
        batch, locations = import_files.parse(await read_file(file), file.filename or "")
    except data_import.ImportRejected as exc:
        return {
            "total": 0,
            "counts": {},
            "records": [],
            "errors": exc.errors,
            "error_count": len(exc.errors),
            "fingerprint": "",
        }
    result = data_import.preview(session, source, batch)
    result["errors"] = [
        {**error, **locations.get((error["entity"], error["external_id"]), {})}
        for error in result["errors"]
    ]
    return result


@router.post("/apply")
async def apply(
    session: DB,
    file: Annotated[UploadFile, File()],
    source: Annotated[Source, Form()],
    fingerprint: Annotated[str, Form(min_length=64, max_length=64)],
    request_id: Annotated[ExternalId, Form()],
):
    global_only(session)
    batch, _ = import_files.parse(await read_file(file), file.filename or "")
    return data_import.apply(session, source, batch, request_id, "file", fingerprint)


@router.get("/history")
def history(session: DB, limit: Annotated[int, Query(ge=1, le=100)] = 50):
    global_only(session)
    return [
        {
            "id": row.id,
            "source": row.source,
            "request_id": row.request_id,
            "channel": row.channel,
            "status": row.status,
            "actor_username": row.actor_username,
            "created_at": row.created_at.replace(tzinfo=UTC).isoformat(),
            "result": {key: value for key, value in row.result.items() if key != "records"},
        }
        for row in session.scalars(select(ImportRun).order_by(ImportRun.id.desc()).limit(limit))
    ]


@router.get("/keys", response_model=list[IntegrationKeyRead])
def keys(session: DB, admin: AdminAccount):
    return session.scalars(select(IntegrationKey).order_by(IntegrationKey.id.desc())).all()


@router.post("/keys", status_code=201)
def create_key(data: IntegrationKeyCreate, session: DB, admin: AdminAccount):
    expiry = (
        data.expires_at.replace(tzinfo=UTC)
        if data.expires_at and data.expires_at.tzinfo is None
        else data.expires_at
    )
    if expiry and expiry <= datetime.now(UTC):
        raise HTTPException(422, "Срок действия должен быть в будущем")
    token = "hrm_" + secrets.token_urlsafe(36)
    key = IntegrationKey(
        name=data.name,
        source=TypeAdapter(Source).validate_python(data.source),
        token_hash=token_hash(token),
        prefix=token[:16],
        entities=list(dict.fromkeys(data.entities)),
        expires_at=expiry,
    )
    session.add(key)
    session.commit()
    return {"key": IntegrationKeyRead.model_validate(key).model_dump(mode="json"), "token": token}


@router.delete("/keys/{key_id}", status_code=204)
def revoke_key(key_id: int, session: DB, admin: AdminAccount):
    key = session.get(IntegrationKey, key_id)
    if not key:
        raise HTTPException(404, "Ключ не найден")
    key.is_active = False
    session.commit()
    return Response(status_code=204)
