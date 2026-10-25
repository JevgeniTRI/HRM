from datetime import date

import pytest
from sqlalchemy import func, select

from app.auth import password_hash, verify_password
from app.database import get_session
from app.models import Account, Department, Employee
from app.seed_expansion import TEAMS, populate_organization


def test_expansion_counts_repeated_run_and_real_role_access(client):
    generator = client.app.dependency_overrides[get_session]()
    session = next(generator)
    try:
        result = populate_organization(session, today=date(2026, 10, 23))
        session.commit()
        assert result["created"] == {"departments": 5, "employees": 65, "accounts": 65}
        assert len({u["username"] for u in result["users"]}) == 65
        for team in TEAMS:
            department = session.scalar(select(Department).where(Department.name == team.name))
            people = session.scalars(
                select(Employee).where(Employee.department_id == department.id)
            ).all()
            assert len(people) == 13
            accounts = session.scalars(
                select(Account).where(Account.employee_id.in_([p.id for p in people]))
            ).all()
            assert sum(a.role == "manager" for a in accounts) == 1
            assert sum(a.role == "employee" for a in accounts) == 12
            assert all(p.about and p.experience and p.education for p in people)
            assert all(p.hired_at <= date(2026, 10, 23) for p in people)

        worker = result["users"][1]
        employee = session.get(Employee, worker["employee_id"])
        account = session.scalar(select(Account).where(Account.username == worker["username"]))
        employee.about = "Резюме изменено пользователем"
        account.password_hash = password_hash("Changed-password-2026")
        saved_hash = account.password_hash
        session.commit()
        again = populate_organization(session, today=date(2026, 11, 1))
        session.commit()
        assert again["created"] == {"departments": 0, "employees": 0, "accounts": 0}
        assert employee.about == "Резюме изменено пользователем"
        assert account.password_hash == saved_hash
        assert verify_password("Changed-password-2026", account.password_hash)
        assert session.scalar(select(func.count(Employee.id))) == 65
    finally:
        generator.close()

    departments = client.get("/api/departments").json()
    assert len(departments) == 5
    assert all(d["employee_count"] == 13 and len(d["managers"]) == 1 for d in departments)
    manager = result["users"][0]
    outsider = result["users"][13]
    login = client.post(
        "/api/auth/login", json={"username": manager["username"], "password": "123"}
    )
    assert login.status_code == 200
    team_page = client.get("/api/employees", params={"page_size": 100}).json()
    assert team_page["total"] == 13
    assert all(p["department_id"] == manager["department_id"] for p in team_page["items"])
    assert client.get(f"/api/employees/{worker['employee_id']}").status_code == 200
    assert client.get(f"/api/employees/{outsider['employee_id']}").status_code == 404
    login = client.post(
        "/api/auth/login",
        json={"username": worker["username"], "password": "Changed-password-2026"},
    )
    assert login.status_code == 200
    assert client.get(f"/api/employees/{worker['employee_id']}").status_code == 200
    assert client.get(f"/api/employees/{manager['employee_id']}").status_code == 404
    assert client.get("/api/accounts").status_code == 403


def test_conflicting_username_rolls_back_entire_expansion(client):
    generator = client.app.dependency_overrides[get_session]()
    session = next(generator)
    try:
        session.add(
            Account(
                username=TEAMS[0].members[1][2],
                password_hash=password_hash("Existing-password-2026"),
                role="admin",
            )
        )
        session.commit()
        with pytest.raises(ValueError, match="уже занят"):
            with session.begin():
                populate_organization(session)
        assert session.scalar(select(func.count(Department.id))) == 0
        assert session.scalar(select(func.count(Employee.id))) == 0
        assert session.scalar(select(func.count(Account.id))) == 2
    finally:
        generator.close()
