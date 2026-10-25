from sqlalchemy import func, or_, select, true, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.errors import ConflictError, NotFoundError, ValidationError
from app.models import Department, Employee, Team
from app.permissions import employee_scope, visible_employee_ids
from app.schemas import TeamRead
from app.services.common import commit, escaped_search, record_activity, require_record
from app.services.organization import apply_reporting_changes


def scope(session):
    actor = session.info.get("actor")
    if actor is None or actor.global_access:
        return true()
    visible = visible_employee_ids(session)
    return (Team.department_id == actor.department_id) & or_(
        Team.manager_id.in_(visible),
        Team.supervisor_id.in_(visible),
        Team.id.in_(select(Employee.team_id).where(employee_scope(session))),
    )


def read_team(session, team_id):
    team = session.scalar(
        select(Team)
        .where(Team.id == team_id, scope(session))
        .options(
            selectinload(Team.department),
            selectinload(Team.manager).selectinload(Employee.department),
            selectinload(Team.supervisor).selectinload(Employee.department),
        )
        .execution_options(populate_existing=True)
    )
    if team is None:
        raise NotFoundError("Команда не найдена")
    count = session.scalar(
        select(func.count(Employee.id)).where(Employee.team_id == team_id, employee_scope(session))
    )
    return TeamRead(
        id=team.id,
        code=team.code,
        name=team.name,
        department=team.department,
        manager=team.manager,
        supervisor=team.supervisor,
        member_count=count,
        version=team.version,
    )


def list_teams(session, department_id=None, q=""):
    query = select(Team.id, Team.name, Team.code).where(scope(session))
    if department_id is not None:
        query = query.where(Team.department_id == department_id)
    return [
        read_team(session, row.id)
        for row in session.execute(query.order_by(Team.name, Team.id))
        if not q.strip() or q.strip().casefold() in f"{row.code} {row.name}".casefold()
    ]


def lock_team(session, team_id, version=None):
    session.execute(update(Team).where(Team.id == team_id).values(version=Team.version))
    team = require_record(session, Team, team_id)
    session.refresh(team)
    if version is not None and version != team.version:
        raise ConflictError("Команда уже изменена. Обновите данные и повторите действие")
    return team


def person_in_department(session, employee_id, department_id):
    if employee_id is None:
        return None
    person = session.get(Employee, employee_id)
    if person is None or person.department_id != department_id:
        raise ValidationError("Руководитель и сотрудники команды должны находиться в одном отделе")
    return person


def create_team(session, data):
    session.execute(
        update(Department).where(Department.id == data.department_id).values(name=Department.name)
    )
    require_record(session, Department, data.department_id)
    manager = person_in_department(session, data.manager_id, data.department_id)
    person_in_department(session, data.supervisor_id, data.department_id)
    if manager and session.scalar(select(Team.id).where(Team.manager_id == manager.id)):
        raise ConflictError("Этот сотрудник уже руководит другой командой")
    reports = (
        session.scalars(select(Employee.id).where(Employee.manager_id == data.manager_id)).all()
        if manager
        else []
    )
    supervisor_id = (
        data.supervisor_id
        if data.supervisor_id is not None
        else manager.manager_id
        if manager
        else None
    )
    team = Team(**{**data.model_dump(), "supervisor_id": supervisor_id})
    session.add(team)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("Код команды уже используется") from exc
    changes = {person: manager.id for person in reports} if manager else {}
    if manager:
        changes[manager.id] = supervisor_id
    apply_reporting_changes(session, changes, {person: team.id for person in reports}, [team.id])
    record_activity(session, "team", "Создана команда", f"{team.code} · {team.name}")
    commit(session, "Не удалось создать команду: код или руководитель уже используется")
    return read_team(session, team.id)


def members(session, team_id, page=1, page_size=50, candidates=False, q="", unassigned_only=False):
    team = read_team(session, team_id)
    query = select(Employee).where(
        Employee.department_id == team.department.id, employee_scope(session)
    )
    if candidates:
        query = query.where(or_(Employee.team_id.is_(None), Employee.team_id != team_id))
        excluded = set()
        cursor = (
            team.manager.id if team.manager else team.supervisor.id if team.supervisor else None
        )
        while cursor is not None and cursor not in excluded:
            excluded.add(cursor)
            cursor = session.scalar(select(Employee.manager_id).where(Employee.id == cursor))
        query = query.where(Employee.id.not_in(excluded))
        if unassigned_only:
            query = query.where(Employee.team_id.is_(None))
    else:
        query = query.where(Employee.team_id == team_id)
    if q.strip():
        query = query.where(Employee.search_text.like(f"%{escaped_search(q)}%", escape="\\"))
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    people = session.scalars(
        query.options(selectinload(Employee.department))
        .order_by(Employee.last_name, Employee.first_name, Employee.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {"items": people, "total": total, "page": page, "page_size": page_size}


def assign_members(session, team_id, employee_ids, version):
    team = lock_team(session, team_id, version)
    ids = set(employee_ids)
    if team.manager_id in ids:
        raise ValidationError("Руководитель не может входить в состав своей команды")
    apply_reporting_changes(
        session,
        {person: team.manager_id or team.supervisor_id for person in ids},
        {person: team_id for person in ids},
        [team_id],
    )
    record_activity(
        session, "team", "Сотрудники назначены в команду", f"{team.code} · {len(ids)} сотрудников"
    )
    commit(session, "Не удалось назначить сотрудников в команду")
    return read_team(session, team_id)


def replace_manager(session, team_id, manager_id, version):
    team = lock_team(session, team_id, version)
    new = person_in_department(session, manager_id, team.department_id)
    if new.id == team.manager_id:
        return read_team(session, team_id)
    if session.scalar(select(Team.id).where(Team.manager_id == new.id, Team.id != team_id)):
        raise ConflictError("Этот сотрудник уже руководит другой командой")
    old = session.get(Employee, team.manager_id) if team.manager_id else None
    ids = set(session.scalars(select(Employee.id).where(Employee.team_id == team_id)))
    # Include existing reporting lines so replacing a position also transfers nested leaders.
    if old:
        ids.update(session.scalars(select(Employee.id).where(Employee.manager_id == old.id)))
    ids.discard(new.id)
    upper_team_id = old.team_id if old else None
    team.manager_id = new.id
    changes = {person: new.id for person in ids}
    memberships = {person: team_id for person in ids}
    touched = {team_id}
    if old:
        children = session.scalars(
            select(Team).where(Team.supervisor_id == old.id, Team.id != team_id)
        ).all()
        for child in children:
            child.supervisor_id = new.id
            touched.add(child.id)
            if child.manager_id is None:
                for person in session.scalars(
                    select(Employee.id).where(Employee.team_id == child.id)
                ):
                    changes[person] = new.id
                    memberships[person] = child.id
    changes[new.id] = team.supervisor_id
    memberships[new.id] = upper_team_id
    if old:
        changes[old.id] = None
        memberships[old.id] = None
    session.flush()
    apply_reporting_changes(session, changes, memberships, touched)
    record_activity(
        session,
        "team",
        "Заменён руководитель команды",
        f"{team.code} · {new.first_name} {new.last_name}",
    )
    commit(session, "Не удалось заменить руководителя команды")
    return read_team(session, team_id)


def remove_member(session, team_id, employee_id, version):
    lock_team(session, team_id, version)
    person = require_record(session, Employee, employee_id)
    if person.team_id != team_id:
        raise NotFoundError("Сотрудник не входит в эту команду")
    apply_reporting_changes(session, {employee_id: None}, {employee_id: None}, [team_id])
    record_activity(
        session,
        "team",
        "Сотрудник выведен из команды",
        f"{person.first_name} {person.last_name}",
        person.id,
    )
    commit(session, "Не удалось вывести сотрудника из команды")


def delete_team(session, team_id, version):
    team = lock_team(session, team_id, version)
    if session.scalar(select(Employee.id).where(Employee.team_id == team_id).limit(1)):
        raise ConflictError("Сначала переведите сотрудников в другую команду")
    record_activity(session, "team", "Удалена команда", f"{team.code} · {team.name}")
    session.delete(team)
    commit(session, "Не удалось удалить команду")
