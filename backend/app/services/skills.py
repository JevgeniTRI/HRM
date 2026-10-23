from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.models import Employee, EmployeeSkill, Skill, utc_now
from app.permissions import visible_employee_ids
from app.schemas import AssessmentWrite, SkillRead, SkillSummary, SkillWrite
from app.services.common import commit, record_activity, require_record
from app.storage import remove_files


def list_skills(session: Session):
    rows = session.execute(
        select(Skill, func.count(EmployeeSkill.id))
        .outerjoin(
            EmployeeSkill,
            (EmployeeSkill.skill_id == Skill.id)
            & EmployeeSkill.employee_id.in_(visible_employee_ids(session)),
        )
        .group_by(Skill.id)
        .order_by(Skill.category, Skill.name_key)
    ).all()
    return [
        SkillSummary(**SkillRead.model_validate(skill).model_dump(), employee_count=count)
        for skill, count in rows
    ]


def create_skill(data: SkillWrite, session: Session):
    skill = Skill(**data.model_dump(), name_key=data.name.casefold())
    session.add(skill)
    record_activity(session, "skill", "Добавлен навык", data.name)
    commit(session, "Навык с таким названием уже существует")
    return skill


def update_skill(skill_id: int, data: SkillWrite, session: Session):
    skill = require_record(session, Skill, skill_id)
    for key, value in data.model_dump().items():
        setattr(skill, key, value)
    skill.name_key = data.name.casefold()
    record_activity(session, "skill", "Обновлён навык", data.name)
    commit(session, "Навык с таким названием уже существует")
    return skill


def delete_skill(skill_id: int, session: Session):
    skill = require_record(session, Skill, skill_id)
    if session.scalar(select(EmployeeSkill.id).where(EmployeeSkill.skill_id == skill_id).limit(1)):
        raise ConflictError("Сначала удалите этот навык из карточек сотрудников")
    record_activity(session, "skill", "Удалён навык", skill.name)
    session.delete(skill)
    commit(session, "Навык назначен сотрудникам")
    return None


def assess_skill(employee_id: int, skill_id: int, data: AssessmentWrite, session: Session):
    employee = require_record(session, Employee, employee_id)
    skill = require_record(session, Skill, skill_id)
    assessment = session.scalar(
        select(EmployeeSkill).where(
            EmployeeSkill.employee_id == employee_id, EmployeeSkill.skill_id == skill_id
        )
    )
    if assessment is None:
        assessment = EmployeeSkill(employee_id=employee_id, skill_id=skill_id)
        session.add(assessment)
    assessment.current_level = data.current_level
    assessment.target_level = data.target_level
    assessment.updated_at = utc_now()
    level = "не оценён" if data.current_level is None else str(data.current_level)
    record_activity(
        session,
        "assessment",
        "Обновлена оценка навыка",
        f"{employee.first_name} {employee.last_name} · "
        f"{skill.name}: {level}, цель {data.target_level}",
        employee.id,
    )
    commit(session, "Оценка была изменена другим запросом. Обновите страницу")
    return assessment


def remove_assessment(employee_id: int, skill_id: int, session: Session):
    employee = require_record(session, Employee, employee_id)
    skill = require_record(session, Skill, skill_id)
    assessment = session.scalar(
        select(EmployeeSkill).where(
            EmployeeSkill.employee_id == employee_id, EmployeeSkill.skill_id == skill_id
        )
    )
    if assessment is None:
        raise NotFoundError("Навык не назначен сотруднику")
    stored_names = [file.stored_name for file in assessment.certificates]
    session.delete(assessment)
    record_activity(
        session,
        "assessment",
        "Удалён навык сотрудника",
        f"{employee.first_name} {employee.last_name} · {skill.name}",
        employee.id,
    )
    commit(session, "Не удалось удалить оценку")
    remove_files(stored_names)
    return None
