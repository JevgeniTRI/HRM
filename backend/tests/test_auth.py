"""Exercise real sessions and roles through HTTP, including object-level access."""

from datetime import UTC, datetime, timedelta

import pytest

from app.auth import COOKIE, password_hash, token_hash, verify_password
from app.database import get_session
from app.models import Account, AuthSession

PASSWORD = "Role-test-password-2026"
HASH = password_hash(PASSWORD)


def login(client, username, password=PASSWORD):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response


def as_admin(client):
    login(client, "admin", "Test-admin-password-2026")


@pytest.fixture
def team(client):
    departments = [
        client.post("/api/departments", json={"name": name}).json() for name in ("Team A", "Team B")
    ]
    people = {}
    for name, department in (
        ("manager", 0),
        ("peer", 0),
        ("worker", 0),
        ("outsider", 1),
        ("power", 1),
    ):
        response = client.post(
            "/api/employees",
            json={
                "first_name": name,
                "last_name": "Person",
                "email": f"{name}@example.com",
                "position": "Engineer",
                "department_id": departments[department]["id"],
                "hired_at": "2026-01-01",
            },
        )
        assert response.status_code == 201, response.text
        people[name] = response.json()
    generator = client.app.dependency_overrides[get_session]()
    session = next(generator)
    try:
        for name, role in (
            ("manager", "manager"),
            ("peer", "manager"),
            ("worker", "employee"),
            ("outsider", "employee"),
            ("power", "power_user"),
        ):
            session.add(
                Account(
                    username=name,
                    password_hash=HASH,
                    role=role,
                    employee_id=people[name]["id"],
                    is_active=True,
                )
            )
        session.commit()
    finally:
        generator.close()
    return {"departments": departments, **people}


def test_anonymous_access_and_csrf(client):
    client.cookies.clear()
    for path in (
        "/api/employees",
        "/api/tasks",
        "/api/departments",
        "/api/skills",
        "/api/dashboard",
        "/api/matrix",
        "/api/accounts",
        "/api/employees/1",
        "/api/employees/export",
    ):
        assert client.get(path).status_code == 401
    assert client.get("/api/health").status_code == 200
    del client.headers["X-HRM-Request"]
    assert (
        client.post(
            "/api/auth/login", json={"username": "admin", "password": "Test-admin-password-2026"}
        ).status_code
        == 403
    )
    client.headers["X-HRM-Request"] = "1"
    as_admin(client)
    del client.headers["X-HRM-Request"]
    assert client.post("/api/departments", json={"name": "Blocked"}).status_code == 403
    assert client.post("/api/auth/logout").status_code == 403


def test_session_cookie_rotation_logout_and_expiration(client):
    old = client.cookies.get(COOKIE)
    response = login(client, "ADMIN", "Test-admin-password-2026")
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    token = client.cookies.get(COOKIE)
    assert old != token
    client.cookies.set(COOKIE, old)
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.clear()
    client.cookies.set(COOKIE, token)
    assert client.get("/api/auth/me").status_code == 200
    generator = client.app.dependency_overrides[get_session]()
    session = next(generator)
    try:
        entry = session.get(AuthSession, token_hash(token))
        assert entry is not None and entry.token_hash != token
        entry.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()
    finally:
        generator.close()
    assert client.get("/api/auth/me").status_code == 401
    as_admin(client)
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_login_error_and_rate_limit(client):
    client.cookies.clear()
    for _ in range(10):
        assert (
            client.post(
                "/api/auth/login", json={"username": "missing", "password": "wrong"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/auth/login", json={"username": "missing", "password": "wrong"}
        ).status_code
        == 429
    )


def test_password_hashes_use_random_salts():
    first = password_hash(PASSWORD)
    second = password_hash(PASSWORD)
    assert first != second and PASSWORD not in first
    assert verify_password(PASSWORD, first)
    assert not verify_password("wrong", first)


@pytest.mark.parametrize(
    "role,expected",
    [
        ("worker", {"worker"}),
        ("manager", {"manager", "peer", "worker"}),
        ("power", {"manager", "peer", "worker", "outsider", "power"}),
    ],
)
def test_employee_lists_counts_and_departments_are_scoped(client, team, role, expected):
    login(client, role)
    page = client.get("/api/employees").json()
    assert page["total"] == len(expected)
    assert {item["first_name"] for item in page["items"]} == expected
    foreign = team["departments"][1]["id"]
    filtered = client.get(f"/api/employees?department_id={foreign}").json()
    assert filtered["total"] == (2 if role == "power" else 0)
    departments = client.get("/api/departments").json()
    assert len(departments) == (2 if role == "power" else 1)
    assert sum(d["employee_count"] for d in departments) == len(expected)
    manager_ids = {m["id"] for department in departments for m in department["managers"]}
    assert manager_ids == (
        set() if role == "worker" else {team["manager"]["id"], team["peer"]["id"]}
    )


def test_department_managers_update_after_account_changes_and_transfers(client, team):
    departments = client.get("/api/departments").json()
    own = next(d for d in departments if d["id"] == team["manager"]["department_id"])
    assert own["employee_count"] == 3
    assert {m["name"] for m in own["managers"]} == {"manager Person", "peer Person"}
    account = next(a for a in client.get("/api/accounts").json() if a["username"] == "peer")
    assert (
        client.put(
            f"/api/accounts/{account['id']}", json={**account, "is_active": False}
        ).status_code
        == 200
    )
    own = next(d for d in client.get("/api/departments").json() if d["id"] == own["id"])
    assert own["managers"] == [{"id": team["manager"]["id"], "name": "manager Person"}]
    other_id = team["outsider"]["department_id"]
    assert (
        client.put(
            f"/api/employees/{team['manager']['id']}",
            json={**team["manager"], "department_id": other_id},
        ).status_code
        == 200
    )
    departments = client.get("/api/departments").json()
    assert next(d for d in departments if d["id"] == own["id"])["managers"] == []
    assert next(d for d in departments if d["id"] == other_id)["managers"] == [
        {"id": team["manager"]["id"], "name": "manager Person"}
    ]


def test_employee_cannot_read_or_change_manager_peer_or_foreign_records(client, team):
    skill = client.post("/api/skills", json={"name": "Python", "category": "Tech"}).json()
    manager = team["manager"]["id"]
    worker = team["worker"]["id"]
    client.put(
        f"/api/employees/{manager}/skills/{skill['id']}",
        json={"current_level": 3, "target_level": 4},
    )
    login(client, "worker")
    for name in ("manager", "peer", "outsider"):
        person = team[name]
        path = f"/api/employees/{person['id']}"
        assert client.get(path).status_code == 404
        assert client.put(path, json={**person, "first_name": "Hacked"}).status_code == 404
        assert client.delete(path).status_code == 404
    for suffix in ("", "/certificates", "/certificates/1/file"):
        assert client.get(f"/api/employees/{manager}/skills/{skill['id']}{suffix}").status_code in (
            404,
            405,
        )
    assert (
        client.put(
            f"/api/employees/{manager}/skills/{skill['id']}", json={"target_level": 4}
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/employees/{manager}/skills/{skill['id']}/certificates",
            files={"file": ("cert.pdf", b"%PDF-1.4\n")},
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/employees/{manager}/skills/{skill['id']}/certificates/1").status_code
        == 404
    )
    assert client.get("/api/employees/export").status_code == 403
    assert client.get("/api/dashboard").status_code == 403
    assert client.get("/api/matrix").status_code == 403
    assert client.get(f"/api/employees/{worker}").status_code == 200
    assert client.get("/api/skills").json()[0]["employee_count"] == 0


def test_employee_can_edit_resume_but_not_employment_or_department(client, team):
    login(client, "worker")
    data = team["worker"]
    path = f"/api/employees/{data['id']}"
    response = client.put(
        path,
        json={
            **data,
            "about": "My resume",
            "experience": "Projects",
            "education": "University",
            "first_name": "Updated",
        },
    )
    assert response.status_code == 200
    assert response.json()["about"] == "My resume"
    for change in (
        {"department_id": team["departments"][1]["id"]},
        {"position": "Boss"},
        {"status": "inactive"},
        {"hired_at": "2020-01-01"},
    ):
        assert client.put(path, json={**data, **change}).status_code == 403
    assert client.delete(path).status_code == 403
    assert client.delete(f"/api/employees/{data['id']:04d}").status_code == 403
    assert client.post("/api/employees", json=data).status_code == 403


def test_manager_can_edit_peer_and_subordinates_only_in_own_department(client, team):
    login(client, "manager")
    for name in ("manager", "peer", "worker"):
        data = team[name]
        response = client.put(f"/api/employees/{data['id']}", json={**data, "position": "Updated"})
        assert response.status_code == 200, response.text
    outsider = team["outsider"]
    assert client.get(f"/api/employees/{outsider['id']}").status_code == 404
    assert client.put(f"/api/employees/{outsider['id']}", json=outsider).status_code == 404
    assert (
        client.put(
            f"/api/employees/{team['worker']['id']}",
            json={**team["worker"], "department_id": outsider["department_id"]},
        ).status_code
        == 403
    )
    matrix = client.get("/api/matrix").json()
    assert matrix["total"] == 3
    dashboard = client.get("/api/dashboard").json()
    assert dashboard["stats"]["employees"] == 3
    assert all(
        event["employee_id"] in {team[n]["id"] for n in ("manager", "peer", "worker")}
        for event in dashboard["activities"]
    )
    exported = client.get("/api/employees/export").text
    assert "outsider@example.com" not in exported and "worker@example.com" in exported


@pytest.mark.parametrize("role", ["worker", "manager", "power"])
def test_only_admin_can_manage_accounts(client, team, role):
    login(client, role)
    assert client.get("/api/accounts").status_code == 403
    assert (
        client.post(
            "/api/accounts", json={"username": "hacker", "password": PASSWORD, "role": "admin"}
        ).status_code
        == 403
    )
    assert (
        client.put(
            "/api/accounts/1", json={"username": "admin", "role": "employee", "is_active": False}
        ).status_code
        == 403
    )
    assert client.put("/api/accounts/1/password", json={"password": PASSWORD}).status_code == 403


def test_power_user_can_manage_all_departments_and_catalogs(client, team):
    login(client, "power")
    assert (
        client.put(
            f"/api/employees/{team['manager']['id']}",
            json={**team["manager"], "department_id": team["departments"][1]["id"]},
        ).status_code
        == 200
    )
    assert client.post("/api/departments", json={"name": "Team C"}).status_code == 201
    assert (
        client.post("/api/skills", json={"name": "Python", "category": "Tech"}).status_code == 201
    )
    assert client.get("/api/dashboard").status_code == 200


def test_account_creation_validation_and_session_revocation(client, team):
    worker_account = next(
        a for a in client.get("/api/accounts").json() if a["username"] == "worker"
    )
    assert "password_hash" not in worker_account
    assert (
        client.post(
            "/api/accounts",
            json={"username": "no-person", "password": PASSWORD, "role": "employee"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/accounts",
            json={
                "username": "duplicate-person",
                "password": PASSWORD,
                "role": "employee",
                "employee_id": team["worker"]["id"],
            },
        ).status_code
        == 409
    )
    login(client, "worker")
    token = client.cookies.get(COOKIE)
    as_admin(client)
    response = client.put(
        f"/api/accounts/{worker_account['id']}", json={**worker_account, "is_active": False}
    )
    assert response.status_code == 200
    client.cookies.clear()
    client.cookies.set(COOKIE, token)
    assert client.get("/api/auth/me").status_code == 401
    assert (
        client.post(
            "/api/auth/login", json={"username": "worker", "password": PASSWORD}
        ).status_code
        == 401
    )


def test_password_change_and_admin_reset_revoke_sessions(client, team):
    worker_account = next(
        a for a in client.get("/api/accounts").json() if a["username"] == "worker"
    )
    login(client, "worker")
    assert (
        client.put(
            "/api/auth/password",
            json={"current_password": "wrong", "new_password": "New-password-2026"},
        ).status_code
        == 400
    )
    assert (
        client.put(
            "/api/auth/password",
            json={"current_password": PASSWORD, "new_password": "New-password-2026"},
        ).status_code
        == 204
    )
    assert client.get("/api/auth/me").status_code == 401
    login(client, "worker", "New-password-2026")
    token = client.cookies.get(COOKIE)
    as_admin(client)
    assert (
        client.put(
            f"/api/accounts/{worker_account['id']}/password", json={"password": PASSWORD}
        ).status_code
        == 204
    )
    client.cookies.clear()
    client.cookies.set(COOKIE, token)
    assert client.get("/api/auth/me").status_code == 401


def test_admin_cannot_lock_self_out(client):
    me = client.get("/api/auth/me").json()
    assert (
        client.put(f"/api/accounts/{me['id']}", json={**me, "is_active": False}).status_code == 409
    )
    assert (
        client.put(f"/api/accounts/{me['id']}", json={**me, "role": "employee"}).status_code == 422
    )


def test_tasks_assignment_scope_summary_and_tampering(client, team):
    dept_a, dept_b = (d["id"] for d in team["departments"])
    tasks = {}
    for name, assignee, departments in (
        ("mine", team["worker"]["id"], [dept_a]),
        ("boss", team["manager"]["id"], [dept_a]),
        ("foreign", team["outsider"]["id"], [dept_b]),
        ("unassigned", None, [dept_a]),
        ("shared", None, [dept_a, dept_b]),
    ):
        response = client.post(
            "/api/tasks",
            json={"title": name, "assignee_id": assignee, "department_ids": departments},
        )
        assert response.status_code == 201, response.text
        tasks[name] = response.json()
    login(client, "worker")
    assert client.get("/api/tasks").json()["total"] == 1
    assert client.get("/api/tasks/summary").json()["total"] == 1
    for name in ("boss", "foreign", "unassigned", "shared"):
        task = tasks[name]
        assert client.get(f"/api/tasks/{task['id']}").status_code == 404
        assert (
            client.put(
                f"/api/tasks/{task['id']}/status",
                json={"status": "done", "version": task["version"]},
            ).status_code
            == 404
        )
        assert client.delete(f"/api/tasks/{task['id']}?version=1").status_code == 404
    mine = tasks["mine"]
    assert (
        client.post(
            "/api/tasks", json={"title": "Hacked", "assignee_id": team["manager"]["id"]}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/tasks", json={"title": "Own", "assignee_id": team["worker"]["id"]}
        ).status_code
        == 201
    )
    assert (
        client.put(
            f"/api/tasks/{mine['id']}",
            json={**mine, "department_ids": [dept_a], "assignee_id": team["manager"]["id"]},
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"/api/tasks/{mine['id']}/status", json={"status": "done", "version": mine["version"]}
        ).status_code
        == 200
    )
    login(client, "manager")
    assert {t["title"] for t in client.get("/api/tasks").json()["items"]} == {
        "mine",
        "boss",
        "unassigned",
        "Own",
    }
    assert client.get("/api/tasks/summary").json()["total"] == 4
    assert (
        client.post(
            "/api/tasks",
            json={
                "title": "Hacked",
                "assignee_id": team["outsider"]["id"],
                "department_ids": [dept_a],
            },
        ).status_code
        == 422
    )
    assert (
        client.post("/api/tasks", json={"title": "Hacked", "department_ids": [dept_b]}).status_code
        == 403
    )
    assert (
        client.post(
            "/api/tasks",
            json={
                "title": "Assigned",
                "assignee_id": team["worker"]["id"],
                "department_ids": [dept_a],
            },
        ).status_code
        == 201
    )
