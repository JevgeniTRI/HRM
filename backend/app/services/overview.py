from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Activity, Employee, EmployeeSkill, Skill
from app.permissions import employee_scope, visible_employee_ids
from app.schemas import DashboardStats, EmployeeStatus, SkillMetric
from app.services.assessment_rules import coverage
from app.services.departments import department_summaries
from app.services.personnel import employee_query


def skill_metrics(session) -> list[SkillMetric]:
    rows = session.execute(
        select(
            Skill,
            func.count(EmployeeSkill.id),
            func.count(EmployeeSkill.current_level),
            func.sum(case((EmployeeSkill.current_level >= EmployeeSkill.target_level, 1), else_=0)),
            func.avg(EmployeeSkill.current_level),
        )
        .outerjoin(
            EmployeeSkill,
            (EmployeeSkill.skill_id == Skill.id)
            & EmployeeSkill.employee_id.in_(visible_employee_ids(session)),
        )
        .group_by(Skill.id)
        .order_by(func.count(EmployeeSkill.id).desc(), Skill.id)
    ).all()
    return [
        SkillMetric(
            id=skill.id,
            name=skill.name,
            category=skill.category,
            assigned=assigned,
            assessed=assessed,
            at_target=at_target or 0,
            coverage=coverage(at_target or 0, assigned),
            average_level=round(average, 1) if average is not None else None,
        )
        for skill, assigned, assessed, at_target, average in rows
    ]


def read_dashboard(session: Session):
    statuses = dict(
        session.execute(
            select(Employee.status, func.count())
            .where(employee_scope(session))
            .group_by(Employee.status)
        ).all()
    )
    metrics = skill_metrics(session)
    assignments = sum(metric.assigned for metric in metrics)
    assessed = sum(metric.assessed for metric in metrics)
    at_target = sum(metric.at_target for metric in metrics)
    departments = department_summaries(session)
    stats = DashboardStats(
        employees=sum(statuses.values()),
        active_employees=statuses.get("active", 0),
        probation_employees=statuses.get("probation", 0),
        leave_employees=statuses.get("leave", 0),
        departments=len(departments),
        skills=len(metrics),
        assignments=assignments,
        assessed=assessed,
        coverage=coverage(at_target, assignments),
        gaps=assessed - at_target,
        unassessed=assignments - assessed,
    )
    activity_query = select(Activity)
    actor = session.info.get("actor")
    if actor and not actor.global_access:
        activity_query = activity_query.where(
            Activity.employee_id.in_(visible_employee_ids(session))
        )
    activities = session.scalars(activity_query.order_by(Activity.id.desc()).limit(6)).all()
    recent = session.scalars(
        select(Employee)
        .where(employee_scope(session))
        .options(selectinload(Employee.department))
        .order_by(Employee.id.desc())
        .limit(5)
    ).all()
    return {
        "stats": stats,
        "departments": departments,
        "skill_metrics": metrics,
        "activities": activities,
        "recent_employees": recent,
    }


def read_matrix(
    session: Session,
    q: str = "",
    department_id: int | None = None,
    status: EmployeeStatus | None = None,
    page: int = 1,
    page_size: int = 20,
):
    query = employee_query(q, department_id, status).where(employee_scope(session))
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    employees = session.scalars(
        query.options(
            selectinload(Employee.department),
            selectinload(Employee.skills).selectinload(EmployeeSkill.skill),
            selectinload(Employee.skills).selectinload(EmployeeSkill.certificates),
        )
        .order_by(Employee.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    skills = session.scalars(select(Skill).order_by(Skill.category, Skill.name_key)).all()
    return {
        "skills": skills,
        "employees": employees,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
