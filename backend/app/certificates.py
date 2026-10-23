from typing import Annotated

from fastapi import APIRouter, File, Form, Query, Response, UploadFile
from fastapi.responses import FileResponse

from app.dependencies import DB
from app.schemas import CertificateRead
from app.services import certificates

router = APIRouter(
    prefix="/employees/{employee_id}/skills/{skill_id}/certificates", tags=["Сертификаты"]
)


@router.get("", response_model=list[CertificateRead])
def list_certificates(employee_id: int, skill_id: int, session: DB):
    return certificates.list_certificates(session, employee_id, skill_id)


@router.post("", response_model=CertificateRead, status_code=201)
def upload_certificate(
    employee_id: int,
    skill_id: int,
    session: DB,
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form(max_length=160)] = "",
):
    try:
        return certificates.upload_certificate(
            session, employee_id, skill_id, file.file, file.filename, title
        )
    finally:
        file.file.close()


@router.get("/{certificate_id}/file")
def read_certificate(
    employee_id: int,
    skill_id: int,
    certificate_id: int,
    session: DB,
    download: Annotated[bool, Query()] = False,
):
    certificate, path = certificates.read_certificate_file(
        session, employee_id, skill_id, certificate_id
    )
    return FileResponse(
        path,
        media_type=certificate.content_type,
        filename=certificate.original_name,
        content_disposition_type="attachment" if download else "inline",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
            "Content-Security-Policy": "sandbox; default-src 'none'; frame-ancestors 'none'",
        },
    )


@router.delete("/{certificate_id}", status_code=204)
def delete_certificate(employee_id: int, skill_id: int, certificate_id: int, session: DB):
    certificates.delete_certificate(session, employee_id, skill_id, certificate_id)
    return Response(status_code=204)
