from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.errors import ConflictError, ValidationError
from app.models import Account, AuthSession, Employee, Team
from app.schemas import OrganizationWrite
from app.services.common import commit, record_activity, require_record


def lock_employee(session: Session, employee_id: int) -> Employee:
    # Acquire SQLite's writer lock before inspecting or changing reporting lines.
    session.execute(
        update(Employee).where(Employee.id == employee_id).values(manager_id=Employee.manager_id)
    )
    employee = require_record(session, Employee, employee_id)
    session.refresh(employee, ["manager_id", "is_manager", "department_id", "team_id"])
    return employee


def require_no_reports(session: Session, employee_id: int):
    if session.scalar(select(Employee.id).where(Employee.manager_id == employee_id).limit(1)):
        raise ConflictError("Сначала назначьте подчинённым другого руководителя")


def reconcile_managers(session: Session, employee_ids):
    """A person's reports determine their status; global account rights are independent."""
    session.flush()
    ids = set(employee_ids) - {None}
    employees = session.scalars(select(Employee).where(Employee.id.in_(ids))).all()
    reports = set(
        session.execute(
            select(Employee.manager_id, Employee.department_id).where(Employee.manager_id.in_(ids))
        ).all()
    )
    accounts = {
        account.employee_id: account
        for account in session.scalars(select(Account).where(Account.employee_id.in_(ids))).all()
    }
    revoked = []
    for employee in employees:
        has_reports = (employee.id, employee.department_id) in reports
        employee.is_manager = has_reports
        account = accounts.get(employee.id)
        if account is not None and account.role in {"employee", "manager"}:
            role = "manager" if has_reports else "employee"
            if account.role != role:
                account.role = role
                revoked.append(account.id)
    if revoked:
        session.execute(delete(AuthSession).where(AuthSession.account_id.in_(revoked)))


def apply_reporting_changes(session: Session, changes: dict, memberships=None, touch_teams=()):
    """Validate a whole batch, then synchronize team membership, hierarchy and access atomically."""
    session.flush()
    rows = session.execute(
        select(Employee.id, Employee.manager_id, Employee.department_id, Employee.team_id)
    ).all()
    people = {row.id: row for row in rows}
    parents = {row.id: row.manager_id for row in rows}
    teams = {team.id: team for team in session.scalars(select(Team)).all()}
    by_manager = {team.manager_id: team for team in teams.values() if team.manager_id is not None}
    affected = set(changes)
    touched = set(touch_teams)
    selected_teams = {}
    for person, parent in changes.items():
        if person not in people or (parent is not None and parent not in people):
            raise ValidationError("Сотрудник или руководитель не найден")
        if person == parent:
            raise ValidationError("Нельзя назначить сотрудника своим руководителем")
        if parent is not None and people[parent].department_id != people[person].department_id:
            raise ValidationError("Руководитель и подчинённые должны находиться в одном отделе")
        team_id = by_manager[parent].id if parent in by_manager else None
        if memberships is not None and person in memberships:
            team_id = memberships[person]
        if team_id is not None:
            team = teams.get(team_id)
            if team is None or team.department_id != people[person].department_id:
                raise ValidationError("Команда и сотрудник должны находиться в одном отделе")
            if team.manager_id == person:
                raise ValidationError("Руководитель не может входить в состав своей команды")
            if parent != (team.manager_id or team.supervisor_id):
                raise ValidationError("Непосредственный руководитель определяется командой")
        selected_teams[person] = team_id
        touched.update([people[person].team_id, team_id])
        affected.update([parents[person], parent])
    parents.update(changes)
    for person in changes:
        visited = set()
        cursor = person
        while cursor is not None:
            if cursor in visited:
                raise ValidationError("Нельзя создать цикл подчинённости")
            visited.add(cursor)
            cursor = parents.get(cursor)
    for person, parent in changes.items():
        session.execute(
            update(Employee)
            .where(Employee.id == person)
            .values(manager_id=parent, team_id=selected_teams[person])
        )
        if person in by_manager:
            by_manager[person].supervisor_id = parent
            touched.add(by_manager[person].id)
    for team_id in touched - {None}:
        teams[team_id].version += 1
    reconcile_managers(session, affected)


def sync_account_manager(session: Session, employee_id: int | None, role: str) -> str:
    if employee_id is None or role in {"admin", "power_user"}:
        return role
    employee = lock_employee(session, employee_id)
    reconcile_managers(session, [employee_id])
    return "manager" if employee.is_manager else "employee"


def update_organization(session: Session, employee_id: int, data: OrganizationWrite):
    employee = lock_employee(session, employee_id)
    if data.kind == "head" and data.manager_id is not None:
        raise ValidationError("У руководителя отдела не может быть непосредственного руководителя")
    if data.kind != "head" and data.manager_id is None:
        raise ValidationError("Выберите непосредственного руководителя в этом отделе")
    if data.manager_id == employee_id:
        raise ValidationError("Нельзя назначить сотрудника своим руководителем")
    # Validate the complete proposed graph before writing any of its edges.
    rows = session.execute(
        select(Employee.id, Employee.manager_id).where(
            Employee.department_id == employee.department_id
        )
    ).all()
    parents = {row.id: row.manager_id for row in rows}
    current_reports = {person for person, parent in parents.items() if parent == employee_id}
    reports = set(data.report_ids) if data.report_ids is not None else current_reports
    if not current_reports <= reports:
        raise ConflictError(
            "Чтобы убрать подчинённого, сначала назначьте ему другого руководителя в его карточке"
        )
    if data.kind == "employee" and reports:
        raise ConflictError(
            "Сотрудник с подчинёнными является руководителем. Сначала переназначьте подчинённых"
        )
    if employee_id in reports:
        raise ValidationError("Нельзя назначить сотрудника своим подчинённым")
    changes = {employee_id: data.manager_id, **{person: employee_id for person in reports}}
    if any(person not in parents for person in changes) or (
        data.manager_id is not None and data.manager_id not in parents
    ):
        raise ValidationError("Руководитель и подчинённые должны находиться в одном отделе")
    parents.update(changes)
    for person in changes:
        visited = set()
        cursor = person
        while cursor is not None:
            if cursor in visited:
                raise ValidationError("Нельзя создать цикл подчинённости")
            visited.add(cursor)
            if cursor not in parents:
                raise ValidationError("В цепочке подчинения есть сотрудник другого отдела")
            cursor = parents[cursor]
    apply_reporting_changes(session, changes)
    record_activity(
        session,
        "organization",
        "Изменена подчинённость",
        f"{employee.first_name} {employee.last_name} · {employee.department.name}",
        employee_id,
    )
    commit(session, "Структура организации была изменена. Обновите данные и повторите действие")
    return employee
