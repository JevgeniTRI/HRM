from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.auth import token_hash
from app.dependencies import DB
from app.import_schemas import ImportBatch, IntegrationRequest
from app.models import IntegrationKey
from app.permissions import Principal
from app.services import data_import

router = APIRouter(prefix="/integrations", tags=["API внешних систем"])
bearer = HTTPBearer(
    auto_error=False, description="Ключ, выданный администратором в разделе «Импорт и интеграции»"
)


def integration_key(
    session: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
):
    key = (
        session.scalar(
            select(IntegrationKey).where(
                IntegrationKey.token_hash == token_hash(credentials.credentials)
            )
        )
        if credentials and credentials.scheme.lower() == "bearer"
        else None
    )
    if (
        not key
        or not key.is_active
        or (key.expires_at and key.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC))
    ):
        raise HTTPException(
            401, "Требуется действующий ключ интеграции", headers={"WWW-Authenticate": "Bearer"}
        )
    session.info["actor"] = Principal(key.id, "power_user", None, None)
    session.info["actor_username"] = f"integration:{key.source}"
    return key


Key = Annotated[IntegrationKey, Depends(integration_key)]


def scoped_batch(data, key):
    batch = ImportBatch.model_validate(data.model_dump(exclude={"request_id"}, exclude_unset=True))
    if any(
        getattr(batch, entity) and entity not in key.entities for entity in ImportBatch.model_fields
    ):
        raise HTTPException(403, "Ключу не разрешён один из типов данных пакета")
    return batch


@router.post("/validate")
def validate(data: IntegrationRequest, session: DB, key: Key):
    return data_import.preview(session, key.source, scoped_batch(data, key))


@router.post("/imports")
def apply(data: IntegrationRequest, session: DB, key: Key):
    result = data_import.apply(session, key.source, scoped_batch(data, key), data.request_id, "api")
    key.last_used_at = datetime.now(UTC)
    session.commit()
    return result
