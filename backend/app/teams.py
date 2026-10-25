from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile

from app.dependencies import DB
from app.errors import ValidationError
from app.schemas import EmployeePage, TeamAssignment, TeamRead, TeamReplacement, TeamWrite
from app.services import team_import
from app.services import teams as service

router = APIRouter(prefix="/teams", tags=["Команды"])


def global_only(session):
    if not session.info["actor"].global_access:
        raise HTTPException(403, "Управлять командами могут только администратор и power_user")


@router.get("", response_model=list[TeamRead])
def list_teams(
    session: DB, department_id: int | None = None, q: Annotated[str, Query(max_length=100)] = ""
):
    return service.list_teams(session, department_id, q)


@router.post("", response_model=TeamRead, status_code=201)
def create_team(data: TeamWrite, session: DB):
    global_only(session)
    return service.create_team(session, data)


@router.get("/import/template")
def template(session: DB):
    global_only(session)
    content = "\ufeff" + ";".join(team_import.HEADERS) + "\r\n"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="team-import-template.csv"'},
    )


async def read_file(file):
    content = await file.read(team_import.MAX_FILE_SIZE + 1)
    if len(content) > team_import.MAX_FILE_SIZE:
        raise ValidationError("Размер файла не должен превышать 5 МБ")
    return content


@router.post("/import/preview")
async def preview(session: DB, file: Annotated[UploadFile, File()]):
    global_only(session)
    _, result = team_import.plan_import(session, await read_file(file), file.filename or "")
    return result


@router.post("/import")
async def import_people(
    session: DB,
    file: Annotated[UploadFile, File()],
    fingerprint: Annotated[str, Form(max_length=64)],
):
    global_only(session)
    return team_import.import_people(
        session, await read_file(file), file.filename or "", fingerprint
    )


@router.get("/{team_id}", response_model=TeamRead)
def read_team(team_id: int, session: DB):
    return service.read_team(session, team_id)


@router.get("/{team_id}/members", response_model=EmployeePage)
def members(
    team_id: int,
    session: DB,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
):
    return service.members(session, team_id, page, page_size)


@router.get("/{team_id}/candidates", response_model=EmployeePage)
def candidates(
    team_id: int,
    session: DB,
    page: Annotated[int, Query(ge=1)] = 1,
    q: Annotated[str, Query(max_length=100)] = "",
    unassigned_only: bool = True,
):
    global_only(session)
    return service.members(
        session, team_id, page, 100, candidates=True, q=q, unassigned_only=unassigned_only
    )


@router.post("/{team_id}/members", response_model=TeamRead)
def assign_members(team_id: int, data: TeamAssignment, session: DB):
    global_only(session)
    return service.assign_members(session, team_id, data.employee_ids, data.version)


@router.put("/{team_id}/manager", response_model=TeamRead)
def replace_manager(team_id: int, data: TeamReplacement, session: DB):
    global_only(session)
    return service.replace_manager(session, team_id, data.manager_id, data.version)


@router.delete("/{team_id}/members/{employee_id}", status_code=204)
def remove_member(
    team_id: int, employee_id: int, session: DB, version: Annotated[int, Query(ge=1)]
):
    global_only(session)
    service.remove_member(session, team_id, employee_id, version)
    return Response(status_code=204)


@router.delete("/{team_id}", status_code=204)
def delete_team(team_id: int, session: DB, version: Annotated[int, Query(ge=1)]):
    global_only(session)
    service.delete_team(session, team_id, version)
    return Response(status_code=204)
