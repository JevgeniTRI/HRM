import copy
import io
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from openpyxl import load_workbook
from sqlalchemy import func, select

from app.database import get_session
from app.models import ImportIdentity, IntegrationKey
from app.services.import_files import EXAMPLE, template


@contextmanager
def db_session(client):
    yield from client.app.dependency_overrides[get_session]()


def key(client, **options):
    result = client.post(
        "/api/imports/keys",
        json={
            "name": "SAP",
            "source": "sap",
            "entities": ["departments", "employees", "teams", "skills"],
            **options,
        },
    )
    assert result.status_code == 201, result.text
    return result.json()


def send(client, payload, token, path="imports"):
    return client.post(
        f"/api/integrations/{path}", json=payload, headers={"Authorization": f"Bearer {token}"}
    )


def test_api_preview_atomic_graph_and_replay(client):
    token = key(client)["token"]
    data = copy.deepcopy(EXAMPLE)
    result = send(client, data, token, "validate")
    assert result.status_code == 200, result.text
    assert result.json()["errors"] == [], result.text
    assert client.get("/api/departments").json() == []
    assert client.get("/api/imports/history").json() == []
    result = send(client, data, token)
    assert result.status_code == 200, result.text
    assert result.json()["total"] == 6
    people = client.get("/api/employees").json()["items"]
    ids = {p["email"]: p["id"] for p in people}
    worker = next(p for p in people if p["email"] == "maria.sap@example.com")
    assert worker["manager_id"] == ids["ivan.sap@example.com"]
    assert send(client, data, token).json()["replayed"] is True
    assert len(client.get("/api/imports/history").json()) == 1
    data["departments"][0]["name"] = "Другой отдел"
    assert send(client, data, token).status_code == 409
    update = {
        "request_id": "second",
        "employees": [{"external_id": "E102", "email": "new@example.com"}],
    }
    result = send(client, update, token)
    assert result.status_code == 200, result.text
    person = client.get(f"/api/employees/{worker['id']}").json()
    assert person["email"] == "new@example.com"
    assert person["manager_id"] == worker["manager_id"]


def test_api_failure_rolls_back_and_records_history(client):
    token = key(client)["token"]
    data = copy.deepcopy(EXAMPLE)
    data["employees"][2]["manager_external_id"] = "E102"
    result = send(client, data, token)
    assert result.status_code == 422, result.text
    assert result.json()["errors"]
    assert client.get("/api/departments").json() == []
    assert client.get("/api/employees").json()["total"] == 0
    assert client.get("/api/imports/history").json()[0]["status"] == "failed"
    assert send(client, EXAMPLE, token).status_code == 409


def test_api_keys_scopes_revocation_and_auth_separation(client):
    created = key(client, entities=["departments"])
    token = created["token"]
    assert send(client, EXAMPLE, token).status_code == 403
    assert send(client, EXAMPLE, "wrong").status_code == 401
    assert client.post("/api/integrations/imports", json=EXAMPLE).status_code == 401
    listed = client.get("/api/imports/keys").json()
    assert "token_hash" not in listed[0] and "token" not in listed[0]
    assert client.delete(f"/api/imports/keys/{created['key']['id']}").status_code == 204
    assert (
        send(client, {"request_id": "x", "departments": EXAMPLE["departments"]}, token).status_code
        == 401
    )
    fresh = key(client)["token"]
    client.cookies.clear()
    assert (
        client.get("/api/accounts", headers={"Authorization": f"Bearer {fresh}"}).status_code == 401
    )
    assert send(client, EXAMPLE, fresh).status_code == 200


def test_file_multisheet_preview_apply_and_stale_state(client):
    book = load_workbook(io.BytesIO(template("xlsx")))
    for entity, records in EXAMPLE.items():
        if entity == "request_id":
            continue
        sheet = book[entity]
        headers = [cell.value for cell in sheet[1]]
        for record in records:
            sheet.append([record.get(header) for header in headers])
    output = io.BytesIO()
    book.save(output)
    book.close()
    files = {"file": ("data.xlsx", output.getvalue())}
    preview = client.post("/api/imports/preview", files=files, data={"source": "manual"})
    assert preview.status_code == 200, preview.text
    assert preview.json()["errors"] == [], preview.text
    assert client.get("/api/teams").json() == []
    assert client.post("/api/departments", json={"name": "Другой"}).status_code == 201
    data = {
        "source": "manual",
        "fingerprint": preview.json()["fingerprint"],
        "request_id": "file-1",
    }
    assert client.post("/api/imports/apply", files=files, data=data).status_code == 409
    data["fingerprint"] = client.post(
        "/api/imports/preview", files=files, data={"source": "manual"}
    ).json()["fingerprint"]
    result = client.post("/api/imports/apply", files=files, data=data)
    assert result.status_code == 200, result.text
    assert result.json()["counts"]["employees"]["created"] == 3


def test_csv_errors_no_partial_import(client):
    content = "entity;external_id;name;email\ndepartments;d;Отдел;\nemployees;p;;invalid\n".encode()
    result = client.post("/api/imports/preview", files={"file": ("test.csv", content)})
    assert result.status_code == 200, result.text
    assert result.json()["error_count"] == 1
    assert result.json()["errors"][0]["line"] == 3
    assert client.get("/api/departments").json() == []


def test_replacement_reassigns_fifty_members_and_nested_team(client):
    token = key(client)["token"]
    data = copy.deepcopy(EXAMPLE)
    basic = data["employees"][2]
    data["employees"] += [
        {**basic, "external_id": f"P{i}", "email": f"person{i}@example.com"} for i in range(50)
    ]
    data["employees"] += [
        {**basic, "external_id": "NEW", "email": "newboss@example.com", "team_external_id": None},
        {**basic, "external_id": "NEST", "email": "nested@example.com"},
    ]
    data["teams"].append(
        {
            "external_id": "NESTTEAM",
            "name": "Вложенная команда",
            "code": "NEST",
            "department_external_id": "D100",
            "manager_external_id": "NEST",
            "supervisor_external_id": "E101",
        }
    )
    result = send(client, data, token)
    assert result.status_code == 200, result.text
    replacement = {
        "request_id": "replace",
        "teams": [{"external_id": "T100", "manager_external_id": "NEW"}],
    }
    result = send(client, replacement, token)
    assert result.status_code == 200, result.text
    teams = client.get("/api/teams").json()
    team = next(t for t in teams if t["code"] == "DEV-100")
    members = client.get(f"/api/teams/{team['id']}/members?page_size=100").json()["items"]
    assert len(members) == 52
    assert all(p["manager_id"] == team["manager"]["id"] for p in members)
    nested = next(t for t in teams if t["code"] == "NEST")
    assert nested["supervisor"]["id"] == team["manager"]["id"]


def test_existing_profiles_assessments_scale_and_optional_text_preserved(client, employee, skill):
    client.put(
        f"/api/employees/{employee['id']}/skills/{skill['id']}",
        json={"current_level": 2, "target_level": 4},
    )
    original_skill = next(
        row for row in client.get("/api/skills").json() if row["id"] == skill["id"]
    )
    token = key(client)["token"]
    payload = {
        "request_id": "bind-existing",
        "employees": [{"external_id": "person", "email": employee["email"], "about": "Импорт"}],
        "skills": [
            {"external_id": "skill", "name": skill["name"], "description": "Новое описание"}
        ],
    }
    result = send(client, payload, token)
    assert result.status_code == 200, result.text
    assert result.json()["counts"]["employees"]["updated"] == 1
    renamed = {
        "request_id": "rename",
        "employees": [{"external_id": "person", "email": "renamed@example.com", "about": None}],
        "skills": [{"external_id": "skill", "name": "Новое название"}],
    }
    assert send(client, renamed, token).status_code == 200
    person = client.get(f"/api/employees/{employee['id']}").json()
    assert person["about"] == ""
    assert person["skills"][0]["current_level"] == 2
    assert person["skills"][0]["target_level"] == 4
    updated_skill = next(
        row for row in client.get("/api/skills").json() if row["id"] == skill["id"]
    )
    assert updated_skill["scale"] == original_skill["scale"]


def test_cross_department_and_cycles_are_rejected(client):
    token = key(client)["token"]
    assert send(client, EXAMPLE, token).status_code == 200
    data = {
        "request_id": "bad-dept",
        "departments": [{"external_id": "D2", "name": "Другой"}],
        "employees": [
            {"external_id": "E102", "department_external_id": "D2", "manager_external_id": "E101"}
        ],
    }
    assert send(client, data, token).status_code == 422
    assert len(client.get("/api/departments").json()) == 1
    cycle = {
        "request_id": "bad-cycle",
        "employees": [{"external_id": "E100", "manager_external_id": "E102"}],
    }
    assert send(client, cycle, token).status_code == 422
    contradict = {
        "request_id": "contradict",
        "employees": [{"external_id": "E101", "manager_external_id": None}],
        "teams": [{"external_id": "T100", "supervisor_external_id": "E100"}],
    }
    assert send(client, contradict, token).status_code == 422


def test_failed_preview_leaves_no_external_identities(client):
    token = key(client)["token"]
    bad = copy.deepcopy(EXAMPLE)
    bad["skills"][0].pop("category")
    result = send(client, bad, token, "validate")
    assert result.status_code == 200 and result.json()["errors"]
    with db_session(client) as session:
        assert session.scalar(select(func.count()).select_from(ImportIdentity)) == 0
    assert client.get("/api/employees").json()["total"] == 0
    assert send(client, EXAMPLE, token).status_code == 200


def test_expired_key_and_privileged_fields_rejected(client):
    token_data = key(client)
    with db_session(client) as session:
        session.get(IntegrationKey, token_data["key"]["id"]).expires_at = datetime.now(
            UTC
        ) - timedelta(days=1)
        session.commit()
    assert send(client, EXAMPLE, token_data["token"]).status_code == 401
    token = key(client)["token"]
    data = copy.deepcopy(EXAMPLE)
    data["employees"][0]["role"] = "admin"
    assert send(client, data, token).status_code == 422
    assert client.get("/api/employees").json()["total"] == 0


def test_concurrent_retry_applies_only_once(client):
    token = key(client)["token"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: send(client, EXAMPLE, token), range(2)))
    assert all(response.status_code == 200 for response in responses), [r.text for r in responses]
    assert sorted(r.json()["replayed"] for r in responses) == [False, True]
    assert len(client.get("/api/imports/history").json()) == 1


@pytest.mark.parametrize("role,expected", [("power_user", 200), ("employee", 403)])
def test_import_access_and_key_admin_only(client, employee, role, expected):
    response = client.post(
        "/api/accounts",
        json={
            "username": "import-user",
            "password": "Test-import-password-2026",
            "role": role,
            "employee_id": employee["id"],
        },
    )
    assert response.status_code == 201, response.text
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "import-user", "password": "Test-import-password-2026"},
        ).status_code
        == 200
    )
    assert client.get("/api/imports/history").status_code == expected
    assert client.get("/api/imports/template/xlsx").status_code == expected
    assert client.get("/api/imports/keys").status_code == 403
    assert (
        client.post(
            "/api/imports/keys",
            json={"name": "Denied", "source": "denied", "entities": ["employees"]},
        ).status_code
        == 403
    )


def test_successful_csv_import_and_null_clearing(client):
    files = {
        "file": (
            "test.csv",
            "entity;external_id;name;description\ndepartments;d;Отдел;Текст\n".encode(),
        )
    }
    preview = client.post("/api/imports/preview", files=files).json()
    assert not preview["errors"]
    result = client.post(
        "/api/imports/apply",
        files=files,
        data={"source": "manual", "fingerprint": preview["fingerprint"], "request_id": "csv-1"},
    )
    assert result.status_code == 200, result.text
    files = {"file": ("clear.csv", b"entity;external_id;description\ndepartments;d;#NULL\n")}
    preview = client.post("/api/imports/preview", files=files).json()
    assert (
        client.post(
            "/api/imports/apply",
            files=files,
            data={"source": "manual", "fingerprint": preview["fingerprint"], "request_id": "csv-2"},
        ).status_code
        == 200
    )
    assert client.get("/api/departments").json()[0]["description"] == ""
