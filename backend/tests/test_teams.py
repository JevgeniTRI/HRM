import io

import pytest
from openpyxl import Workbook

from app.auth import COOKIE, password_hash
from app.database import get_session
from app.models import Account

PASSWORD = "Team-test-password-2026"
HASH = password_hash(PASSWORD)


def person(client, department, name):
    result = client.post(
        "/api/employees",
        json={
            "first_name": name,
            "last_name": "Person",
            "email": f"{name}@example.com",
            "position": "Engineer",
            "department_id": department["id"],
            "hired_at": "2026-01-01",
        },
    )
    assert result.status_code == 201, result.text
    return result.json()


@pytest.fixture
def structure(client, department):
    other = client.post("/api/departments", json={"name": "Other"}).json()
    people = {
        name: person(client, other if name == "foreign" else department, name)
        for name in ("head", "old", "new", "worker", "foreign", "power")
    }
    generator = client.app.dependency_overrides[get_session]()
    session = next(generator)
    try:
        for name in ("head", "old", "new", "worker", "foreign", "power"):
            session.add(
                Account(
                    username=name,
                    password_hash=HASH,
                    role="power_user" if name == "power" else "employee",
                    employee_id=people[name]["id"],
                )
            )
        session.commit()
    finally:
        generator.close()
    result = client.post(
        "/api/teams",
        json={
            "code": "DEV-01",
            "name": "Team One",
            "department_id": department["id"],
            "manager_id": people["old"]["id"],
            "supervisor_id": people["head"]["id"],
        },
    )
    assert result.status_code == 201, result.text
    return {"team": result.json(), "department": department, **people}


def assign(client, team_id, ids):
    team = client.get(f"/api/teams/{team_id}").json()
    return client.post(
        f"/api/teams/{team_id}/members", json={"employee_ids": ids, "version": team["version"]}
    )


def login(client, name):
    response = client.post("/api/auth/login", json={"username": name, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()


def admin(client):
    response = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Test-admin-password-2026"}
    )
    assert response.status_code == 200


def upload(client, data, endpoint="preview", fingerprint=None, filename="people.csv"):
    return client.post(
        "/api/teams/import" + ("/preview" if endpoint == "preview" else ""),
        files={"file": (filename, data)},
        data={"fingerprint": fingerprint} if fingerprint else {},
    )


def csv_people(count, code="DEV-01"):
    return (
        "email;team_code;first_name;last_name;position;hired_at\n"
        + "\n".join(
            f"import-{i}@example.com;{code};User{i};Imported;Engineer;2026-01-01"
            for i in range(count)
        )
    ).encode()


def test_csv_preview_commit_and_replacement_transfer_fifty_people(client, structure):
    data = csv_people(50)
    before = client.get("/api/employees").json()["total"]
    preview = upload(client, data)
    assert preview.status_code == 200, preview.text
    assert preview.json()["create_count"] == 50
    assert client.get("/api/employees").json()["total"] == before
    result = upload(client, data, "commit", preview.json()["fingerprint"])
    assert result.status_code == 200, result.text
    assert result.json()["create_count"] == 50
    team_id = structure["team"]["id"]
    members = client.get(f"/api/teams/{team_id}/members?page_size=100").json()
    assert members["total"] == 50
    ids = {p["id"] for p in members["items"]}
    login(client, "old")
    token = client.cookies.get(COOKIE)
    client.cookies.clear()
    admin(client)
    team = client.get(f"/api/teams/{team_id}").json()
    replacement = client.put(
        f"/api/teams/{team_id}/manager",
        json={"manager_id": structure["new"]["id"], "version": team["version"]},
    )
    assert replacement.status_code == 200, replacement.text
    assert replacement.json()["member_count"] == 50
    assert replacement.json()["supervisor"]["id"] == structure["head"]["id"]
    for p in client.get(f"/api/teams/{team_id}/members?page_size=100").json()["items"]:
        assert p["manager_id"] == structure["new"]["id"] and p["team_id"] == team_id
    assert {
        p["id"] for p in client.get(f"/api/teams/{team_id}/members?page_size=100").json()["items"]
    } == ids
    client.cookies.clear()
    client.cookies.set(COOKIE, token)
    assert client.get("/api/auth/me").status_code == 401
    assert login(client, "old")["role"] == "employee"
    assert client.get("/api/employees").json()["total"] == 1
    assert login(client, "new")["role"] == "manager"
    assert client.get("/api/employees").json()["total"] == 51
    login(client, "head")
    assert client.get("/api/employees").json()["total"] == 52


def test_replacement_with_member_preserves_position_and_nested_team(client, structure):
    top = client.post(
        "/api/teams",
        json={
            "code": "TOP",
            "name": "Leadership",
            "department_id": structure["department"]["id"],
            "manager_id": structure["head"]["id"],
        },
    ).json()
    assert assign(client, top["id"], [structure["old"]["id"]]).status_code == 200
    assert (
        assign(
            client, structure["team"]["id"], [structure["new"]["id"], structure["worker"]["id"]]
        ).status_code
        == 200
    )
    nested = client.post(
        "/api/teams",
        json={
            "code": "NEST",
            "name": "Nested",
            "department_id": structure["department"]["id"],
            "manager_id": structure["worker"]["id"],
            "supervisor_id": structure["old"]["id"],
        },
    )
    assert nested.status_code == 201, nested.text
    team = client.get(f"/api/teams/{structure['team']['id']}").json()
    result = client.put(
        f"/api/teams/{team['id']}/manager",
        json={"manager_id": structure["new"]["id"], "version": team["version"]},
    )
    assert result.status_code == 200, result.text
    new = client.get(f"/api/employees/{structure['new']['id']}").json()
    assert new["team_id"] == top["id"] and new["manager_id"] == structure["head"]["id"]
    assert client.get(f"/api/teams/{nested.json()['id']}").json()["supervisor"]["id"] == new["id"]
    assert (
        client.get(f"/api/employees/{structure['worker']['id']}").json()["manager_id"] == new["id"]
    )


def test_batch_assignment_rejects_foreign_and_cycles_atomically(client, structure):
    team = structure["team"]
    for ids in (
        [structure["worker"]["id"], structure["foreign"]["id"]],
        [structure["head"]["id"]],
        [structure["old"]["id"]],
    ):
        result = assign(client, team["id"], ids)
        assert result.status_code == 422, result.text
        assert client.get(f"/api/teams/{team['id']}").json()["member_count"] == 0
    assert client.get(f"/api/employees/{structure['worker']['id']}").json()["team_id"] is None
    result = client.put(
        f"/api/teams/{team['id']}/manager",
        json={"manager_id": structure["foreign"]["id"], "version": team["version"]},
    )
    assert result.status_code == 422
    candidates = client.get(f"/api/teams/{team['id']}/candidates").json()
    assert structure["head"]["id"] not in {person["id"] for person in candidates["items"]}


def test_stale_team_and_import_previews_do_not_overwrite_changes(client, structure):
    team = structure["team"]
    data = csv_people(2)
    preview = upload(client, data).json()
    assert assign(client, team["id"], [structure["worker"]["id"]]).status_code == 200
    assert upload(client, data, "commit", preview["fingerprint"]).status_code == 409
    assert (
        client.post(
            f"/api/teams/{team['id']}/members",
            json={"employee_ids": [structure["new"]["id"]], "version": team["version"]},
        ).status_code
        == 409
    )
    assert client.get("/api/employees?q=Imported").json()["total"] == 0


def test_import_existing_people_keeps_profiles_and_is_repeatable(client, structure):
    worker = structure["worker"]
    data = f"email,team_code,first_name\n{worker['email']},DEV-01,Overwrite".encode()
    for _ in range(2):
        preview = upload(client, data)
        assert preview.status_code == 200, preview.text
        result = upload(client, data, "commit", preview.json()["fingerprint"])
        assert result.status_code == 200, result.text
    saved = client.get(f"/api/employees/{worker['id']}").json()
    assert saved["first_name"] == worker["first_name"]
    assert saved["manager_id"] == structure["old"]["id"]
    assert result.json()["unchanged_count"] == 1


def test_import_errors_and_xlsx_preview(client, structure):
    bad = (
        b"email;team_code\nworker@example.com;UNKNOWN\n"
        b"foreign@example.com;DEV-01\nworker@example.com;DEV-01"
    )
    preview = upload(client, bad)
    assert preview.status_code == 200, preview.text
    assert preview.json()["error_count"] == 3
    assert upload(client, bad, "commit", preview.json()["fingerprint"]).status_code == 422
    book = Workbook()
    sheet = book.active
    sheet.append(["email", "team_code"])
    sheet.append([structure["worker"]["email"], "DEV-01"])
    stream = io.BytesIO()
    book.save(stream)
    response = upload(client, stream.getvalue(), filename="people.xlsx")
    assert response.status_code == 200, response.text
    assert response.json()["assign_count"] == 1
    committed = upload(
        client, stream.getvalue(), "commit", response.json()["fingerprint"], filename="people.xlsx"
    )
    assert committed.status_code == 200, committed.text
    sheet["A2"] = '=HYPERLINK("test")'
    stream = io.BytesIO()
    book.save(stream)
    assert upload(client, stream.getvalue(), filename="formulas.xlsx").status_code == 422


@pytest.mark.parametrize(
    "filename,data",
    [("broken.xlsx", b"not-a-workbook"), ("broken.csv", b"\x98"), ("old.xls", b"legacy")],
)
def test_import_rejects_unreadable_files(client, filename, data):
    assert upload(client, data, filename=filename).status_code == 422


@pytest.mark.parametrize("role", ["old", "worker", "foreign"])
def test_team_read_scope_and_mutations_are_protected(client, structure, role):
    assert assign(client, structure["team"]["id"], [structure["worker"]["id"]]).status_code == 200
    login(client, role)
    team_id = structure["team"]["id"]
    result = client.get(f"/api/teams/{team_id}/members")
    assert result.status_code == (404 if role == "foreign" else 200)
    if role != "foreign":
        assert result.json()["total"] == 1
    assert (
        client.post(
            f"/api/teams/{team_id}/members",
            json={"employee_ids": [structure["new"]["id"]], "version": 1},
        ).status_code
        == 403
    )
    assert client.get(f"/api/teams/{team_id}/candidates").status_code == 403
    assert upload(client, csv_people(1)).status_code == 403
    if role == "foreign":
        assert client.get("/api/teams").json() == []


def test_power_user_can_manage_teams_without_account_administration(client, structure):
    login(client, "power")
    assert assign(client, structure["team"]["id"], [structure["worker"]["id"]]).status_code == 200
    assert client.get("/api/accounts").status_code == 403


def test_personnel_edits_keep_team_membership_consistent(client, structure):
    team = structure["team"]
    assert assign(client, team["id"], [structure["worker"]["id"]]).status_code == 200
    result = client.put(
        f"/api/employees/{structure['new']['id']}/organization",
        json={"kind": "employee", "manager_id": structure["old"]["id"]},
    )
    assert result.status_code == 200, result.text
    assert result.json()["team_id"] == team["id"]
    version = client.get(f"/api/teams/{team['id']}").json()["version"]
    assert client.delete(f"/api/teams/{team['id']}?version={version}").status_code == 409
    result = client.put(
        f"/api/employees/{structure['worker']['id']}",
        json={**structure["worker"], "department_id": structure["foreign"]["department_id"]},
    )
    assert result.status_code == 200, result.text
    assert result.json()["team_id"] is None


def test_twelve_teams_with_fifty_people_import_as_one_file(client, structure):
    codes = ["DEV-01"]
    for index in range(2, 13):
        leader = person(client, structure["department"], f"leader{index}")
        code = f"DEV-{index:02}"
        response = client.post(
            "/api/teams",
            json={
                "code": code,
                "name": f"Team {index}",
                "department_id": structure["department"]["id"],
                "manager_id": leader["id"],
                "supervisor_id": structure["head"]["id"],
            },
        )
        assert response.status_code == 201, response.text
        codes.append(code)
    rows = ["email;team_code;first_name;last_name;position;hired_at"]
    for index, code in enumerate(codes):
        rows.extend(
            f"bulk-{index}-{member}@example.com;{code};User{member};Bulk;Engineer;2026-01-01"
            for member in range(50)
        )
    content = "\n".join(rows).encode()
    preview = upload(client, content)
    assert preview.status_code == 200, preview.text
    assert preview.json()["total"] == 600 and len(preview.json()["rows"]) == 100
    result = upload(client, content, "commit", preview.json()["fingerprint"])
    assert result.status_code == 200, result.text
    assert result.json()["create_count"] == 600
    assert all(team["member_count"] == 50 for team in client.get("/api/teams").json())
    login(client, "head")
    assert client.get("/api/employees").json()["total"] == 613


def test_replacement_preserves_vacant_subteams(client, structure):
    child = client.post(
        "/api/teams",
        json={
            "code": "VACANT",
            "name": "Vacant",
            "department_id": structure["department"]["id"],
            "supervisor_id": structure["old"]["id"],
        },
    ).json()
    assert assign(client, child["id"], [structure["worker"]["id"]]).status_code == 200
    team = client.get(f"/api/teams/{structure['team']['id']}").json()
    result = client.put(
        f"/api/teams/{team['id']}/manager",
        json={"manager_id": structure["new"]["id"], "version": team["version"]},
    )
    assert result.status_code == 200, result.text
    child_after = client.get(f"/api/teams/{child['id']}").json()
    assert child_after["member_count"] == 1
    assert child_after["supervisor"]["id"] == structure["new"]["id"]
    assert (
        client.get(f"/api/employees/{structure['worker']['id']}").json()["team_id"] == child["id"]
    )


def test_creating_team_preserves_existing_manager_and_parent_team(client, structure):
    assert assign(client, structure["team"]["id"], [structure["worker"]["id"]]).status_code == 200
    result = client.post(
        "/api/teams",
        json={
            "code": "CHILD",
            "name": "Child",
            "department_id": structure["department"]["id"],
            "manager_id": structure["worker"]["id"],
        },
    )
    assert result.status_code == 201, result.text
    assert result.json()["supervisor"]["id"] == structure["old"]["id"]
    worker = client.get(f"/api/employees/{structure['worker']['id']}").json()
    assert worker["team_id"] == structure["team"]["id"]
