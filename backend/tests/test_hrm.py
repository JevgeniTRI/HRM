import csv
import io

import pytest


def test_empty_dashboard(client):
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    stats = response.json()["stats"]
    assert stats["employees"] == stats["coverage"] == stats["unassessed"] == 0


def test_employee_persists_and_can_be_updated(client, employee, employee_data, department):
    employee_id = employee["id"]
    assert (
        client.get(f"/api/employees/{employee_id}").json()["department"]["id"] == department["id"]
    )
    result = client.put(
        f"/api/employees/{employee_id}",
        json={
            **employee_data,
            "first_name": "Ольга",
            "status": "leave",
        },
    )
    assert result.status_code == 200
    assert client.get("/api/employees", params={"q": "ОЛЬГА"}).json()["total"] == 1
    assert client.get("/api/dashboard").json()["stats"]["leave_employees"] == 1


def test_duplicate_email_is_conflict_and_activity_atomic(client, employee, employee_data):
    before = len(client.get("/api/dashboard").json()["activities"])
    result = client.post("/api/employees", json={**employee_data, "email": "ANNA@example.com"})
    assert result.status_code == 409
    assert client.get("/api/employees").json()["total"] == 1
    assert len(client.get("/api/dashboard").json()["activities"]) == before


def test_duplicate_update_does_not_change_employee(client, employee, employee_data):
    other = client.post(
        "/api/employees", json={**employee_data, "email": "other@example.com"}
    ).json()
    result = client.put(f"/api/employees/{other['id']}", json=employee_data)
    assert result.status_code == 409
    assert client.get(f"/api/employees/{other['id']}").json()["email"] == "other@example.com"


def test_unicode_search_and_literal_wildcards(client, employee, employee_data):
    assert client.get("/api/employees", params={"q": "МОРОЗОВА"}).json()["total"] == 1
    assert client.get("/api/employees", params={"q": "Морозова Анна"}).json()["total"] == 1
    assert client.get("/api/employees", params={"q": "%"}).json()["total"] == 0
    assert client.get("/api/employees", params={"q": "_"}).json()["total"] == 0


def test_filtering_pagination_and_export(client, employee, employee_data):
    for i in range(11):
        client.post(
            "/api/employees",
            json={**employee_data, "email": f"person{i}@example.com", "status": "probation"},
        )
    first = client.get("/api/employees", params={"page_size": 5}).json()
    second = client.get("/api/employees", params={"page_size": 5, "page": 2}).json()
    assert first["total"] == second["total"] == 12
    assert len(first["items"]) == len(second["items"]) == 5
    assert {e["id"] for e in first["items"]}.isdisjoint({e["id"] for e in second["items"]})
    assert client.get("/api/employees", params={"status": "active"}).json()["total"] == 1
    exported = client.get("/api/employees/export", params={"status": "probation"})
    rows = list(csv.reader(io.StringIO(exported.content.decode("utf-8-sig")), delimiter=";"))
    assert len(rows) == 12
    assert rows[0][0] == "Имя"


def test_missing_department_does_not_create_employee(client, employee_data):
    response = client.post("/api/employees", json={**employee_data, "department_id": 999})
    assert response.status_code == 404
    assert client.get("/api/employees").json()["total"] == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"email": "bad"},
        {"status": "unknown"},
        {"first_name": "   "},
        {"hired_at": "2026-02-31"},
    ],
)
def test_employee_validation(client, employee_data, changes):
    assert client.post("/api/employees", json={**employee_data, **changes}).status_code == 422


def test_department_and_skill_uniqueness_casefold(client, department, skill):
    assert client.post("/api/departments", json={"name": " РАЗРАБОТКА "}).status_code == 409
    assert (
        client.post("/api/skills", json={"name": " python ", "category": "Технические"}).status_code
        == 409
    )


def test_used_department_and_skill_cannot_be_deleted(client, employee, skill, department):
    client.put(
        f"/api/employees/{employee['id']}/skills/{skill['id']}",
        json={"current_level": 2, "target_level": 4},
    )
    assert client.delete(f"/api/departments/{department['id']}").status_code == 409
    assert client.delete(f"/api/skills/{skill['id']}").status_code == 409
    assert (
        client.get(f"/api/employees/{employee['id']}").json()["skills"][0]["skill"]["id"]
        == skill["id"]
    )


def test_assessment_upsert_keeps_single_assignment_and_distinguishes_null(client, employee, skill):
    path = f"/api/employees/{employee['id']}/skills/{skill['id']}"
    response = client.put(path, json={"current_level": None, "target_level": 4})
    assert response.status_code == 200
    assert response.json()["state"] == "unassessed"
    stats = client.get("/api/dashboard").json()["stats"]
    assert stats["unassessed"] == stats["assignments"] == 1
    assert stats["gaps"] == stats["assessed"] == 0
    assert client.put(path, json={"current_level": 0, "target_level": 4}).json()["state"] == "gap"
    stats = client.get("/api/dashboard").json()["stats"]
    assert stats["assessed"] == stats["gaps"] == 1
    assert stats["unassessed"] == 0
    client.put(path, json={"current_level": 5, "target_level": 4})
    person = client.get(f"/api/employees/{employee['id']}").json()
    assert len(person["skills"]) == 1
    assert person["skills"][0]["current_level"] == 5
    assert person["skills"][0]["state"] == "met"
    assert client.get("/api/dashboard").json()["stats"]["coverage"] == 100


@pytest.mark.parametrize("current,target", [(6, 3), (-1, 3), (2, 0), (2, 6), (2.5, 3)])
def test_assessment_validates_level_range(client, employee, skill, current, target):
    assert (
        client.put(
            f"/api/employees/{employee['id']}/skills/{skill['id']}",
            json={
                "current_level": current,
                "target_level": target,
            },
        ).status_code
        == 422
    )


def test_dashboard_coverage_and_average_use_assignments_and_assessed_only(client, employee, skill):
    skills = [skill] + [
        client.post("/api/skills", json={"name": name, "category": "Тест"}).json()
        for name in ["React", "SQL"]
    ]
    for item, current in zip(skills, [4, 2, None], strict=True):
        client.put(
            f"/api/employees/{employee['id']}/skills/{item['id']}",
            json={"current_level": current, "target_level": 3},
        )
    data = client.get("/api/dashboard").json()
    assert data["stats"]["coverage"] == 33
    assert data["stats"]["gaps"] == data["stats"]["unassessed"] == 1
    assert data["skill_metrics"][2]["average_level"] is None
    assert [metric["coverage"] for metric in data["skill_metrics"]] == [100, 0, 0]


def test_delete_employee_cascades_assessments_preserves_activity(
    client, employee, skill, department
):
    client.put(
        f"/api/employees/{employee['id']}/skills/{skill['id']}",
        json={"current_level": 4, "target_level": 3},
    )
    assert client.delete(f"/api/employees/{employee['id']}").status_code == 204
    dashboard = client.get("/api/dashboard").json()
    assert dashboard["stats"]["assignments"] == dashboard["stats"]["employees"] == 0
    assert all(activity["employee_id"] is None for activity in dashboard["activities"])
    assert client.delete(f"/api/skills/{skill['id']}").status_code == 204
    assert client.delete(f"/api/departments/{department['id']}").status_code == 204


def test_matrix_and_employee_profile_share_assessments(client, employee, skill):
    client.put(
        f"/api/employees/{employee['id']}/skills/{skill['id']}",
        json={"current_level": 3, "target_level": 5},
    )
    matrix = client.get("/api/matrix", params={"q": "АННА"}).json()
    profile = client.get(f"/api/employees/{employee['id']}").json()
    assert matrix["total"] == 1
    assert matrix["employees"][0]["skills"] == profile["skills"]
    assert client.get("/api/matrix", params={"department_id": 999}).json()["total"] == 0


def test_remove_assessment(client, employee, skill):
    path = f"/api/employees/{employee['id']}/skills/{skill['id']}"
    client.put(path, json={"current_level": 4, "target_level": 3})
    assert client.delete(path).status_code == 204
    assert client.get(f"/api/employees/{employee['id']}").json()["skills"] == []
    assert client.delete(path).status_code == 404


def test_csv_neutralizes_formula_cells(client, employee_data):
    client.post("/api/employees", json={**employee_data, "first_name": "=SUM(1+1)"})
    csv_data = client.get("/api/employees/export").content.decode("utf-8-sig")
    assert "'=SUM(1+1)" in csv_data


@pytest.mark.parametrize(
    "url", ["/api/employees/999", "/api/employees?page=0", "/api/matrix?page_size=101"]
)
def test_not_found_and_pagination_validation(client, url):
    assert client.get(url).status_code in (404, 422)
