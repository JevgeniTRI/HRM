from datetime import date

from sqlalchemy import func, select

from app.database import get_session
from app.models import Account, Department, Employee, EmployeeSkill, Skill
from app.seed_matrix_demo import HARD_SKILLS, SOFT_SKILLS, populate_matrix_demo


def test_matrix_demo_is_complete_valid_and_idempotent(client):
    generator = client.app.dependency_overrides[get_session]()
    session = next(generator)
    try:
        result = populate_matrix_demo(session, today=date(2026, 10, 25))
        session.commit()
        assert result == {
            "departments": 7,
            "employees": 50,
            "soft_skills": 7,
            "hard_skills": 7,
            "assessments": 700,
            "normalized_assessments": 0,
            "total_employees": 50,
            "total_skills": 14,
        }
        assert session.scalar(select(func.count(Department.id))) == 7
        assert session.scalar(select(func.count(Employee.id))) == 50
        assert session.scalar(select(func.count(Account.id))) == 1
        assert session.scalar(select(func.count(Skill.id))) == 14
        assert session.scalar(select(func.count(EmployeeSkill.id))) == 700
        assert (
            session.scalar(
                select(func.count(EmployeeSkill.id)).where(
                    (EmployeeSkill.current_level < 0)
                    | (EmployeeSkill.current_level > 5)
                    | (EmployeeSkill.target_level < EmployeeSkill.current_level)
                    | (EmployeeSkill.target_level > 5)
                )
            )
            == 0
        )
        assert {
            item.name
            for item in session.scalars(select(Skill).where(Skill.category == "Гибкие навыки"))
        } == set(SOFT_SKILLS)
        assert {
            item.name
            for item in session.scalars(select(Skill).where(Skill.category == "Технические"))
        } == set(HARD_SKILLS)

        again = populate_matrix_demo(session, today=date(2026, 11, 1))
        session.commit()
        assert again["departments"] == 0
        assert again["employees"] == 0
        assert again["soft_skills"] == 0
        assert again["hard_skills"] == 0
        assert again["assessments"] == 0
        assert again["normalized_assessments"] == 0
    finally:
        generator.close()
