"""Exercise real sessions and roles through HTTP, including object-level access."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest

from app.auth import COOKIE, password_hash, token_hash, verify_password
from app.database import get_session
from app.models import Account, AuthSession, Employee

PASSWORD = "Role-test-password-2026"
HASH = password_hash(PASSWORD)


def login(client, username, password=PASSWORD):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response


def as_admin(client):
    login(client, "admin", "Test-admin-password-2026")


@pytest.mark.parametrize(
    "role,expected", [("admin", 200), ("power", 200), ("manager", 403), ("worker", 403)]
)
def test_only_global_roles_can_configure_skill_scales(client, team, role, expected):
    skill = client.post("/api/skills", json={"name": "Scale test", "category": "Tech"}).json()
    if role != "admin":
        login(client, role)
    response = client.put(
        f"/api/skills/{skill['id']}",
        json={
            **skill,
            "scale": {
                "type": "letter",
                "min": 0,
                "max": 25,
                "names": {"25": "Эксперт"},
                "descriptions": {"25": "Обучает команду"},
            },
        },
    )
    assert response.status_code == expected, response.text
    persisted = next(item for item in client.get("/api/skills").json() if item["id"] == skill["id"])
    assert persisted["scale"]["type"] == ("letter" if expected == 200 else "numeric")


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
        session.get(Employee, people["manager"]["id"]).is_manager = True
        peer = session.get(Employee, people["peer"]["id"])
        peer.is_manager = True
        peer.manager_id = people["manager"]["id"]
        session.get(Employee, people["worker"]["id"]).manager_id = peer.id
        session.commit()
    finally:
        generator.close()
    return {"departments": departments, **people}


def test_anonymous_access_and_csrf(client):
    client.cookies.clear()
    for path in (
        "/api/employees",
        "/api/tasks",
        "/api/tasks/calendar?from_on=2026-10-01&to_on=2026-10-31",
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


@pytest.mark.parametrize(
    "role,expected",
    [("worker", {"worker"}), ("manager", {"worker"}), ("power", {"worker", "outsider"})],
)
def test_training_calendar_respects_task_visibility(client, team, role, expected):
    for name in ("worker", "outsider"):
        response = client.post(
            "/api/tasks",
            json={
                "title": name,
                "learning_source": "internal",
                "learning_format": "individual",
                "participant_count": 1,
                "assignee_id": team[name]["id"],
                "department_ids": [team[name]["department_id"]],
                "start_on": "2026-10-01",
                "end_on": "2026-10-31",
            },
        )
        assert response.status_code == 201, response.text
    login(client, role)
    response = client.get("/api/tasks/calendar?from_on=2026-10-01&to_on=2026-10-31")
    assert response.status_code == 200, response.text
    assert {task["title"] for task in response.json()["items"]} == expected


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


def test_admin_account_list_includes_employee_names_without_passwords(client, team):
    response = client.get("/api/accounts")
    assert response.status_code == 200
    accounts = {a["username"]: a for a in response.json()}
    assert accounts["admin"]["employee_name"] is None
    assert accounts["worker"]["employee_name"] == "worker Person"
    assert all("password_hash" not in a for a in accounts.values())
    renamed = client.put(
        f"/api/employees/{team['worker']['id']}",
        json={**team["worker"], "first_name": "Фёдор", "last_name": "Соколов"},
    )
    assert renamed.status_code == 200
    updated = next(a for a in client.get("/api/accounts").json() if a["username"] == "worker")
    assert updated["employee_name"] == "Фёдор Соколов"


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
        == 409
    )
    departments = client.get("/api/departments").json()
    assert next(d for d in departments if d["id"] == own["id"])["managers"] == [
        {"id": team["manager"]["id"], "name": "manager Person"}
    ]
    assert next(d for d in departments if d["id"] == other_id)["managers"] == []


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


def test_manager_can_edit_subordinate_managers_and_employees_only_in_own_tree(client, team):
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
            f"/api/employees/{team['worker']['id']}",
            json={**team["worker"], "department_id": team["departments"][1]["id"]},
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
        "Own",
    }
    assert client.get("/api/tasks/summary").json()["total"] == 3
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


def organization(client, person, kind="employee", manager_id=None, report_ids=None):
    data = {"kind": kind, "manager_id": manager_id}
    if report_ids is not None:
        data["report_ids"] = report_ids
    return client.put(f"/api/employees/{person['id']}/organization", json=data)


def new_person(client, team, name="new", department=0):
    response = client.post(
        "/api/employees",
        json={
            **team["worker"],
            "first_name": name,
            "email": f"{name}@example.com",
            "department_id": team["departments"][department]["id"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("role", ["admin", "power"])
def test_organization_global_roles_can_assign_department_head_and_intermediate(client, team, role):
    leaf = new_person(client, team)
    login(client, "worker")
    old_token = client.cookies.get(COOKIE)
    client.cookies.clear()
    as_admin(client)
    if role == "power":
        login(client, role)
    response = organization(
        client, team["worker"], "intermediate", team["peer"]["id"], [leaf["id"]]
    )
    assert response.status_code == 200, response.text
    assert response.json()["organization_role"] == "intermediate"
    assert response.json()["manager"]["id"] == team["peer"]["id"]
    client.cookies.clear()
    client.cookies.set(COOKIE, old_token)
    assert client.get("/api/auth/me").status_code == 401
    assert login(client, "worker").json()["role"] == "manager"
    assert client.get("/api/employees").json()["total"] == 2
    client.cookies.clear()
    as_admin(client)
    response = organization(client, team["worker"], "head")
    assert response.status_code == 200, response.text
    assert response.json()["organization_role"] == "head"
    assert response.json()["manager"] is None
    assert response.json()["is_manager"] is True
    assert (
        client.get(f"/api/employees/{team['peer']['id']}").json()["organization_role"] == "employee"
    )


def test_organization_preserves_global_account_rights(client, team):
    admin_person = new_person(client, team, "director")
    accounts = client.get("/api/accounts").json()
    admin = next(a for a in accounts if a["username"] == "admin")
    response = client.put(
        f"/api/accounts/{admin['id']}", json={**admin, "employee_id": admin_person["id"]}
    )
    assert response.status_code == 200, response.text
    as_admin(client)
    assert (
        organization(client, admin_person, "head", report_ids=[team["manager"]["id"]]).status_code
        == 200
    )
    assert client.get("/api/auth/me").json()["role"] == "admin"
    login(client, "power")
    assert (
        organization(client, team["power"], "head", report_ids=[team["outsider"]["id"]]).status_code
        == 200
    )
    assert client.get("/api/auth/me").json()["role"] == "power_user"
    assert client.get("/api/employees").json()["total"] == 6


@pytest.mark.parametrize("role", ["worker", "manager", "peer"])
def test_organization_cannot_be_changed_by_employee_or_manager(client, team, role):
    login(client, role)
    assert organization(client, team[role], "head").status_code == 403
    assert organization(client, team["worker"], "head").status_code == 403
    response = client.put(
        f"/api/employees/{team[role]['id']}",
        json={
            **team[role],
            "is_manager": True,
            "manager_id": None,
            "organization_role": "head",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["is_manager"] == (role != "worker")
    assert (
        response.json()["manager_id"]
        == {"worker": team["peer"]["id"], "manager": None, "peer": team["manager"]["id"]}[role]
    )


@pytest.mark.parametrize(
    "invalid",
    [
        "self",
        "cycle",
        "foreign",
        "missing",
        "orphan",
        "head_parent",
        "self_report",
        "foreign_report",
    ],
)
def test_organization_rejects_invalid_reporting_lines(client, team, invalid):
    person, kind, parent, reports = {
        "self": ("manager", "intermediate", team["manager"]["id"], None),
        "cycle": ("manager", "intermediate", team["worker"]["id"], None),
        "foreign": ("worker", "employee", team["outsider"]["id"], None),
        "missing": ("worker", "employee", 999999, None),
        "orphan": ("worker", "employee", None, None),
        "head_parent": ("manager", "head", team["outsider"]["id"], None),
        "self_report": ("worker", "intermediate", team["peer"]["id"], [team["worker"]["id"]]),
        "foreign_report": ("worker", "intermediate", team["peer"]["id"], [team["outsider"]["id"]]),
    }[invalid]
    response = organization(client, team[person], kind, parent, reports)
    assert response.status_code == 422, response.text
    unchanged = client.get(f"/api/employees/{team[person]['id']}").json()
    assert unchanged["manager_id"] == (team["peer"]["id"] if person == "worker" else None)


def test_organization_first_report_promotes_and_last_report_automatically_demotes(client, team):
    leaf = new_person(client, team)
    assert organization(client, leaf, "head").json()["organization_role"] == "employee"
    login(client, "peer")
    old_token = client.cookies.get(COOKIE)
    client.cookies.clear()
    as_admin(client)
    response = organization(client, team["worker"], "employee", leaf["id"])
    assert response.status_code == 200, response.text
    promoted = client.get(f"/api/employees/{leaf['id']}").json()
    assert promoted["organization_role"] == "head" and promoted["is_manager"]
    demoted = client.get(f"/api/employees/{team['peer']['id']}").json()
    assert demoted["organization_role"] == "employee" and not demoted["is_manager"]
    client.cookies.clear()
    client.cookies.set(COOKIE, old_token)
    assert client.get("/api/auth/me").status_code == 401
    assert login(client, "peer").json()["role"] == "employee"
    assert client.get("/api/dashboard").status_code == 403
    as_admin(client)
    assert (
        organization(client, team["worker"], "employee", team["manager"]["id"]).status_code == 200
    )
    assert not client.get(f"/api/employees/{leaf['id']}").json()["is_manager"]


def test_organization_protects_reports_from_accidental_removal_and_head_deletion(client, team):
    assert organization(client, team["peer"], "employee", team["manager"]["id"]).status_code == 409
    assert organization(client, team["manager"], "head", report_ids=[]).status_code == 409
    assert client.delete(f"/api/employees/{team['peer']['id']}").status_code == 409
    assert (
        client.put(
            f"/api/employees/{team['peer']['id']}",
            json={
                **team["peer"],
                "department_id": team["departments"][1]["id"],
            },
        ).status_code
        == 409
    )


def test_organization_department_boundaries_cover_lists_profiles_counts_exports_and_files(
    client, team
):
    # Defend against a legacy path that leaves and re-enters a department.
    other = new_person(client, team, "same_department_outside_branch")
    generator = client.app.dependency_overrides[get_session]()
    session = next(generator)
    try:
        session.get(Employee, team["outsider"]["id"]).manager_id = team["manager"]["id"]
        session.get(Employee, other["id"]).manager_id = team["outsider"]["id"]
        session.commit()
    finally:
        generator.close()
    skill = client.post("/api/skills", json={"name": "Hierarchy", "category": "Tech"}).json()
    certificates = {}
    for name in ("worker", "outsider"):
        path = f"/api/employees/{team[name]['id']}/skills/{skill['id']}"
        assert client.put(path, json={"current_level": 2, "target_level": 4}).status_code == 200
        response = client.post(path + "/certificates", files={"file": ("test.pdf", b"%PDF-1.4\n")})
        assert response.status_code == 201, response.text
        certificates[name] = path + f"/certificates/{response.json()['id']}/file"
    login(client, "manager")
    visible = {team[n]["id"] for n in ("manager", "peer", "worker")}
    assert {p["id"] for p in client.get("/api/employees").json()["items"]} == visible
    assert (
        client.get(f"/api/employees?department_id={team['outsider']['department_id']}").json()[
            "total"
        ]
        == 0
    )
    assert client.get("/api/matrix").json()["total"] == 3
    assert client.get("/api/dashboard").json()["stats"]["employees"] == 3
    assert client.get("/api/skills").json()[0]["employee_count"] == 1
    assert len(client.get("/api/departments").json()) == 1
    assert client.get(f"/api/employees/{team['outsider']['id']}").status_code == 404
    assert client.get(f"/api/employees/{other['id']}").status_code == 404
    detail = client.get(f"/api/employees/{team['manager']['id']}").json()
    assert [p["id"] for p in detail["direct_reports"]] == [team["peer"]["id"]]
    assert client.get(certificates["worker"]).status_code == 200
    assert client.get(certificates["outsider"]).status_code == 404
    exported = client.get("/api/employees/export").text
    assert "worker@example.com" in exported and "outsider@example.com" not in exported
    assert "same_department_outside_branch" not in exported
    login(client, "peer")
    assert client.get("/api/employees").json()["total"] == 2
    assert client.get(f"/api/employees/{team['manager']['id']}").status_code == 404
    detail = client.get(f"/api/employees/{team['peer']['id']}").json()
    assert detail["organization_role"] == "intermediate"
    assert "email" not in detail["manager"] and "skills" not in detail["manager"]


def test_organization_reassignment_changes_existing_ancestor_access_immediately(client, team):
    # Keep one other direct report so the old head stays a manager and retains its session.
    spare = new_person(client, team, "spare")
    destination = new_person(client, team, "destination")
    assert organization(client, spare, manager_id=team["manager"]["id"]).status_code == 200
    login(client, "manager")
    token = client.cookies.get(COOKIE)
    client.cookies.clear()
    as_admin(client)
    assert organization(client, team["peer"], "intermediate", destination["id"]).status_code == 200
    client.cookies.clear()
    client.cookies.set(COOKIE, token)
    assert client.get("/api/auth/me").status_code == 200
    assert client.get("/api/employees").json()["total"] == 2
    assert client.get(f"/api/employees/{team['worker']['id']}").status_code == 404
    assert client.get(f"/api/employees/{team['peer']['id']}").status_code == 404


def test_organization_task_access_stays_inside_department_and_reporting_tree(client, team):
    login(client, "manager")
    response = client.post(
        "/api/tasks",
        json={
            "title": "Nested report training",
            "assignee_id": team["worker"]["id"],
            "department_ids": [team["manager"]["department_id"]],
            "learning_source": "internal",
            "learning_format": "individual",
            "participant_count": 1,
            "start_on": "2026-10-01",
            "end_on": "2026-10-31",
        },
    )
    assert response.status_code == 201, response.text
    assert client.post("/api/tasks", json={"title": "Unassigned"}).status_code == 422
    assert (
        client.post(
            "/api/tasks", json={"title": "Foreign", "assignee_id": team["outsider"]["id"]}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/tasks",
            json={
                "title": "Foreign department",
                "assignee_id": team["worker"]["id"],
                "department_ids": [team["outsider"]["department_id"]],
            },
        ).status_code
        == 403
    )
    assert client.get("/api/tasks/summary").json()["total"] == 1
    assert (
        client.get("/api/tasks/calendar?from_on=2026-10-01&to_on=2026-10-31").json()["total"] == 1
    )


def test_organization_concurrent_parent_changes_cannot_create_a_cycle(client, team):
    other = new_person(client, team)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            pool.submit(organization, client, team["manager"], "intermediate", other["id"]),
            pool.submit(organization, client, other, "intermediate", team["manager"]["id"]),
        ]
        assert sorted(result.result().status_code for result in results) == [200, 422]


def test_organization_account_role_is_derived_even_when_admin_requests_manager(client, team):
    account = next(a for a in client.get("/api/accounts").json() if a["username"] == "outsider")
    response = client.put(f"/api/accounts/{account['id']}", json={**account, "role": "manager"})
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "employee"
    account = next(a for a in client.get("/api/accounts").json() if a["username"] == "peer")
    response = client.put(f"/api/accounts/{account['id']}", json={**account, "role": "employee"})
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "manager"


def test_organization_department_transfer_detaches_parent_and_demotes_last_supervisor(client, team):
    response = client.put(
        f"/api/employees/{team['worker']['id']}",
        json={
            **team["worker"],
            "department_id": team["outsider"]["department_id"],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["manager_id"] is None
    assert response.json()["organization_role"] == "employee"
    assert not client.get(f"/api/employees/{team['peer']['id']}").json()["is_manager"]
    login(client, "manager")
    assert client.get(f"/api/employees/{team['worker']['id']}").status_code == 404


def test_organization_deleting_last_report_restores_employee_status(client, team):
    leaf = new_person(client, team)
    response = organization(client, leaf, manager_id=team["worker"]["id"])
    assert response.status_code == 200, response.text
    assert (
        client.get(f"/api/employees/{team['worker']['id']}").json()["organization_role"]
        == "intermediate"
    )
    assert client.delete(f"/api/employees/{leaf['id']}").status_code == 204
    assert (
        client.get(f"/api/employees/{team['worker']['id']}").json()["organization_role"]
        == "employee"
    )
    assert login(client, "worker").json()["role"] == "employee"
