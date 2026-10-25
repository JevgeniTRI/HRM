"""One transactional import pipeline shared by files and machine clients."""

import hashlib
import json

from pydantic import ValidationError as PydanticError
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.errors import ConflictError, ValidationError
from app.models import Department, Employee, ImportIdentity, ImportRun, Skill, Team
from app.schemas import EmployeeWrite
from app.services.common import record_activity
from app.services.organization import apply_reporting_changes, reconcile_managers
from app.services.personnel import employee_values

MODELS = {"departments": Department, "employees": Employee, "teams": Team, "skills": Skill}
TARGETS = {
    "departments": "department_id",
    "employees": "employee_id",
    "teams": "team_id",
    "skills": "skill_id",
}


class ImportRejected(ValidationError):
    def __init__(self, errors):
        super().__init__("Импорт отменён. Исправьте ошибки и повторите проверку")
        self.errors = errors


def snapshot(session):
    return {
        name: {row["id"]: dict(row) for row in session.execute(select(model.__table__)).mappings()}
        for name, model in MODELS.items()
    }


def fingerprint(session):
    data = snapshot(session)
    data["identities"] = [
        dict(row)
        for row in session.execute(
            select(ImportIdentity.__table__).order_by(ImportIdentity.id)
        ).mappings()
    ]
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def batch_hash(batch):
    return hashlib.sha256(
        json.dumps(batch.model_dump(mode="json", exclude_unset=True), sort_keys=True).encode()
    ).hexdigest()


def lock_import(session):
    # A real outer transaction is essential before SQLite SAVEPOINT preview/rollback.
    session.execute(update(Department).values(name=Department.name))


def _stage(session, source, batch):
    before = snapshot(session)
    context = {"entity": "batch", "external_id": ""}
    records = []

    def resolve(entity, external_id):
        if external_id is None:
            return None
        link = session.scalar(
            select(ImportIdentity).where(
                ImportIdentity.source == source,
                ImportIdentity.entity == entity,
                ImportIdentity.external_id == external_id,
            )
        )
        if link is None:
            raise ValidationError(
                f"Не найден {entity}: external_id={external_id}. "
                "Передайте связанную запись в этом пакете или импортируйте её ранее "
                "с тем же источником"
            )
        return session.get(MODELS[entity], getattr(link, TARGETS[entity]))

    def find(entity, record, natural):
        context.update(entity=entity, external_id=record.external_id)
        link = session.scalar(
            select(ImportIdentity).where(
                ImportIdentity.source == source,
                ImportIdentity.entity == entity,
                ImportIdentity.external_id == record.external_id,
            )
        )
        if link:
            return session.get(MODELS[entity], getattr(link, TARGETS[entity]))
        return (
            session.scalar(select(MODELS[entity]).where(natural)) if natural is not None else None
        )

    def bind(entity, record, obj):
        session.flush()
        link = session.scalar(
            select(ImportIdentity).where(
                ImportIdentity.source == source,
                ImportIdentity.entity == entity,
                ImportIdentity.external_id == record.external_id,
            )
        )
        if link is None:
            session.add(
                ImportIdentity(
                    source=source,
                    entity=entity,
                    external_id=record.external_id,
                    **{TARGETS[entity]: obj.id},
                )
            )
            session.flush()
        records.append({"entity": entity, "external_id": record.external_id, "id": obj.id})

    try:
        for row in batch.departments:
            obj = find(
                "departments", row, Department.name_key == row.name.casefold() if row.name else None
            )
            if obj is None:
                if not row.name:
                    raise ValidationError("Для нового отдела обязательно название name")
                obj = Department(name=row.name, name_key=row.name.casefold(), description="")
                session.add(obj)
            if "name" in row.model_fields_set:
                if not row.name:
                    raise ValidationError("Название отдела нельзя очистить")
                obj.name, obj.name_key = row.name, row.name.casefold()
            if "description" in row.model_fields_set:
                obj.description = row.description or ""
            bind("departments", row, obj)

        employee_rows = {}
        transferred = set()
        for row in batch.employees:
            obj = find(
                "employees", row, Employee.email == str(row.email).casefold() if row.email else None
            )
            values = {key: getattr(obj, key) for key in EmployeeWrite.model_fields} if obj else {}
            for key in EmployeeWrite.model_fields:
                if key in row.model_fields_set:
                    value = getattr(row, key)
                    values[key] = (
                        value or "" if key in {"about", "experience", "education"} else value
                    )
            if "department_external_id" in row.model_fields_set:
                department = resolve("departments", row.department_external_id)
                if department is None:
                    raise ValidationError("Отдел сотрудника нельзя очистить")
                values["department_id"] = department.id
            validated = EmployeeWrite.model_validate(values)
            if obj is None:
                obj = Employee(**employee_values(validated))
                session.add(obj)
            else:
                if obj.department_id != validated.department_id:
                    transferred.add(obj.id)
                for key, value in employee_values(validated).items():
                    setattr(obj, key, value)
            bind("employees", row, obj)
            employee_rows[obj.id] = row

        team_rows, replacements, touched = {}, [], set()
        # Stage every team's metadata before wiring any cross-record relationships.
        for row in batch.teams:
            obj = find("teams", row, Team.code == row.code if row.code else None)
            if obj is None:
                if not row.name or not row.code or not row.department_external_id:
                    raise ValidationError(
                        "Для новой команды нужны name, code и department_external_id"
                    )
                obj = Team(
                    name=row.name,
                    code=row.code,
                    department_id=resolve("departments", row.department_external_id).id,
                )
                session.add(obj)
            for key in ("name", "code"):
                if key in row.model_fields_set:
                    if getattr(row, key) is None:
                        raise ValidationError(f"Поле {key} нельзя очистить")
                    setattr(obj, key, getattr(row, key))
            if "department_external_id" in row.model_fields_set:
                department = resolve("departments", row.department_external_id)
                if department is None:
                    raise ValidationError("Отдел команды нельзя очистить")
                obj.department_id = department.id
            bind("teams", row, obj)
            team_rows[obj.id] = row

        teams = {obj.id: obj for obj in session.scalars(select(Team))}
        employees = {obj.id: obj for obj in session.scalars(select(Employee))}
        for team_id, row in team_rows.items():
            context.update(entity="teams", external_id=row.external_id)
            team = teams[team_id]
            if "supervisor_external_id" in row.model_fields_set:
                boss = resolve("employees", row.supervisor_external_id)
                team.supervisor_id = boss.id if boss else None
            if "manager_external_id" in row.model_fields_set:
                manager = resolve("employees", row.manager_external_id)
                new_id = manager.id if manager else None
                if new_id != team.manager_id:
                    old = employees.get(team.manager_id)
                    if (
                        old is None
                        and manager
                        and "supervisor_external_id" not in row.model_fields_set
                    ):
                        team.supervisor_id = manager.manager_id
                    replacements.append(
                        (
                            team,
                            old.id if old else None,
                            new_id,
                            old.team_id if old else manager.team_id if manager else None,
                        )
                    )
        # Release unique leadership slots first, allowing an atomic swap of two managers.
        for team, _, _, _ in replacements:
            team.manager_id = None
        session.flush()
        new_managers = {new_id for _, _, new_id, _ in replacements if new_id}
        for team, old_id, new_id, upper_team in replacements:
            team.manager_id = new_id
            if old_id:
                for child in teams.values():
                    incoming = team_rows.get(child.id)
                    if (
                        child.id != team.id
                        and child.supervisor_id == old_id
                        and not (incoming and "supervisor_external_id" in incoming.model_fields_set)
                    ):
                        child.supervisor_id = new_id or team.supervisor_id
                for employee in employees.values():
                    if (
                        employee.manager_id == old_id
                        and employee.id != new_id
                        and employee.team_id is None
                    ):
                        employee.team_id = team.id
                if old_id not in new_managers:
                    employees[old_id].manager_id = None
                    employees[old_id].team_id = None
            if new_id:
                employees[new_id].manager_id = team.supervisor_id
                employees[new_id].team_id = upper_team
            touched.add(team.id)

        by_manager = {}
        for team in teams.values():
            if team.manager_id:
                if team.manager_id in by_manager:
                    raise ValidationError("Один сотрудник не может руководить двумя командами")
                by_manager[team.manager_id] = team
        for person_id in transferred:
            employees[person_id].team_id = None
            employees[person_id].manager_id = None
        for person_id, row in employee_rows.items():
            context.update(entity="employees", external_id=row.external_id)
            person = employees[person_id]
            if "team_external_id" in row.model_fields_set:
                team = resolve("teams", row.team_external_id)
                person.team_id = team.id if team else None
                if team is None and "manager_external_id" not in row.model_fields_set:
                    person.manager_id = None
            if "manager_external_id" in row.model_fields_set:
                manager = resolve("employees", row.manager_external_id)
                person.manager_id = manager.id if manager else None
                if "team_external_id" not in row.model_fields_set:
                    person.team_id = (
                        by_manager[person.manager_id].id
                        if person.manager_id in by_manager
                        else None
                    )
                if person_id in by_manager:
                    managed = by_manager[person_id]
                    incoming = team_rows.get(managed.id)
                    if (
                        incoming
                        and "supervisor_external_id" in incoming.model_fields_set
                        and managed.supervisor_id != person.manager_id
                    ):
                        raise ValidationError(
                            "Руководитель сотрудника противоречит "
                            "supervisor_external_id его команды"
                        )
                    managed.supervisor_id = person.manager_id
        for person in employees.values():
            row = employee_rows.get(person.id)
            if person.team_id:
                team = teams[person.team_id]
                parent = team.manager_id or team.supervisor_id
                if (
                    row
                    and "manager_external_id" in row.model_fields_set
                    and person.manager_id != parent
                ):
                    raise ValidationError(
                        f"employees {row.external_id}: руководитель противоречит выбранной команде"
                    )
                person.manager_id = parent
                if person.id in by_manager:
                    managed = by_manager[person.id]
                    incoming = team_rows.get(managed.id)
                    if (
                        incoming
                        and "supervisor_external_id" in incoming.model_fields_set
                        and managed.supervisor_id != parent
                    ):
                        raise ValidationError(
                            "Вышестоящий руководитель команды противоречит "
                            "подчинённости её начальника"
                        )
                    managed.supervisor_id = parent
            elif person.id in by_manager:
                person.manager_id = by_manager[person.id].supervisor_id
            elif person.manager_id in by_manager:
                person.team_id = by_manager[person.manager_id].id

        context.update(entity="organization", external_id="")
        for team in teams.values():
            for leader_id in (team.manager_id, team.supervisor_id):
                if leader_id and employees[leader_id].department_id != team.department_id:
                    raise ValidationError(
                        f"Команда {team.code}: руководитель должен находиться в её отделе"
                    )
        parents = {person.id: person.manager_id for person in employees.values()}
        for person in employees.values():
            if (
                person.manager_id
                and employees[person.manager_id].department_id != person.department_id
            ):
                raise ValidationError(
                    f"Сотрудник ID {person.id}: начальник находится в другом отделе"
                )
            if person.team_id and (
                teams[person.team_id].department_id != person.department_id
                or teams[person.team_id].manager_id == person.id
            ):
                raise ValidationError(
                    f"Сотрудник ID {person.id}: неверный отдел команды "
                    "или членство в собственной команде"
                )
            visited, cursor = set(), person.id
            while cursor is not None:
                if cursor in visited:
                    raise ValidationError("Нельзя создать цикл подчинённости")
                visited.add(cursor)
                cursor = parents.get(cursor)
        changes = {}
        for person in employees.values():
            old = before["employees"].get(person.id, {})
            if (old.get("manager_id"), old.get("team_id"), old.get("department_id")) != (
                person.manager_id,
                person.team_id,
                person.department_id,
            ):
                changes[person.id] = person.manager_id
                touched.update([old.get("team_id"), person.team_id])
        for team in teams.values():
            old = before["teams"].get(team.id, {})
            if any(
                old.get(key) != getattr(team, key)
                for key in ("name", "code", "department_id", "manager_id", "supervisor_id")
            ):
                touched.add(team.id)
        apply_reporting_changes(
            session,
            changes,
            {person_id: employees[person_id].team_id for person_id in changes},
            touched - {None},
        )
        reconcile_managers(session, employees.keys())

        for row in batch.skills:
            obj = find("skills", row, Skill.name_key == row.name.casefold() if row.name else None)
            if obj is None:
                if not row.name or not row.category:
                    raise ValidationError("Для нового навыка нужны name и category")
                obj = Skill(
                    name=row.name,
                    name_key=row.name.casefold(),
                    category=row.category,
                    description="",
                )
                session.add(obj)
            for key in ("name", "category", "description"):
                if key in row.model_fields_set:
                    value = getattr(row, key)
                    if key != "description" and not value:
                        raise ValidationError(f"Поле {key} нельзя очистить")
                    setattr(obj, key, value or "")
            obj.name_key = obj.name.casefold()
            bind("skills", row, obj)
        session.flush()
        after = snapshot(session)
        counts = {entity: {"created": 0, "updated": 0, "unchanged": 0} for entity in MODELS}
        for record in records:
            entity, local_id = record["entity"], record["id"]
            old, new = before[entity].get(local_id), after[entity][local_id]
            record["action"] = (
                "created"
                if old is None
                else "updated"
                if any(old[key] != value for key, value in new.items() if key != "version")
                else "unchanged"
            )
            counts[entity][record["action"]] += 1
            record["label"] = (
                f"{new['first_name']} {new['last_name']}" if entity == "employees" else new["name"]
            )
        return {
            "total": len(records),
            "counts": counts,
            "records": records,
            "affected_employees": sum(
                old != after["employees"].get(local_id)
                for local_id, old in before["employees"].items()
            ),
        }
    except (ValidationError, PydanticError, IntegrityError) as exc:
        message = (
            "Конфликт email, кода, названия или внешнего ID"
            if isinstance(exc, IntegrityError)
            else "Для нового сотрудника нужны first_name, last_name, email, position, "
            "hired_at и department_external_id; обязательные поля нельзя очистить"
            if isinstance(exc, PydanticError)
            else str(exc)
        )
        raise ImportRejected([{**context, "message": message}]) from exc


def preview(session, source, batch):
    lock_import(session)
    state = fingerprint(session)
    nested = session.begin_nested()
    try:
        result = _stage(session, source, batch)
        result.update(errors=[], error_count=0)
    except ImportRejected as exc:
        result = {
            "total": sum(len(getattr(batch, entity)) for entity in MODELS),
            "counts": {},
            "records": [],
            "errors": exc.errors,
            "error_count": len(exc.errors),
        }
    finally:
        nested.rollback()
        session.rollback()
    result["fingerprint"] = state
    result["records"] = result["records"][:100]
    return result


def apply(session, source, batch, request_id, channel, expected_fingerprint=None):
    lock_import(session)
    digest = batch_hash(batch)
    previous = session.scalar(
        select(ImportRun).where(ImportRun.source == source, ImportRun.request_id == request_id)
    )
    if previous:
        if previous.payload_hash != digest:
            raise ConflictError("Этот request_id уже использован для другого пакета")
        if previous.status == "failed":
            raise ImportRejected(previous.result["errors"])
        return {**previous.result, "replayed": True}
    if expected_fingerprint and fingerprint(session) != expected_fingerprint:
        raise ConflictError("Данные изменились после проверки. Проверьте файл ещё раз")
    nested = session.begin_nested()
    errors = None
    try:
        result = _stage(session, source, batch)
        nested.commit()
    except ImportRejected as exc:
        nested.rollback()
        errors = exc.errors
        result = {"total": sum(len(getattr(batch, entity)) for entity in MODELS), "errors": errors}
    run = ImportRun(
        source=source,
        request_id=request_id,
        channel=channel,
        status="failed" if errors else "success",
        actor_username=session.info.get("actor_username", "integration"),
        payload_hash=digest,
        result=result,
    )
    session.add(run)
    session.flush()
    result = {**result, "run_id": run.id, "replayed": False}
    run.result = result
    if not errors:
        record_activity(
            session, "import", "Выполнен импорт данных", f"{source} · {result['total']} записей"
        )
    session.commit()
    if errors:
        raise ImportRejected(errors)
    return result
