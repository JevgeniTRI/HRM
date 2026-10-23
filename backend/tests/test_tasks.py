from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import build_engine
from app.errors import ConflictError
from app.services.common import commit
from app.tasks.models import Task


@pytest.fixture
def training_data(department):
    return {
        "title": "Обучение Python",
        "description": "Практика в команде",
        "status": "todo",
        "learning_source": "internal",
        "learning_format": "group",
        "participant_count": 10,
        "duration_hours": "1.5",
        "cost": "123.45",
        "currency": "EUR",
        "department_ids": [department["id"]],
        "due_on": "2026-11-01",
    }


@pytest.fixture
def task(client, training_data):
    response = client.post("/api/tasks", json=training_data)
    assert response.status_code == 201, response.text
    return response.json()


def test_training_effort_and_exact_cost_persist(client, task):
    persisted = client.get(f"/api/tasks/{task['id']}").json()
    assert Decimal(persisted["person_hours"]) == Decimal("15")
    assert Decimal(persisted["cost"]) == Decimal("123.45")
    assert persisted["departments"][0]["name"] == "Разработка"
    assert persisted["version"] == 1
    preview = client.post(
        "/api/tasks/estimate", json={"duration_hours": "1.5", "participant_count": 10}
    )
    assert preview.status_code == 200
    assert Decimal(preview.json()["person_hours"]) == Decimal(persisted["person_hours"])


def test_ordinary_task_and_unknown_training_duration(client, training_data):
    ordinary = client.post("/api/tasks", json={"title": "Подготовить план развития"})
    assert ordinary.status_code == 201
    assert ordinary.json()["person_hours"] is None
    response = client.post(
        "/api/tasks", json={**training_data, "duration_hours": None, "cost": None, "currency": None}
    )
    assert response.status_code == 201
    assert response.json()["person_hours"] is None
    summary = client.get("/api/tasks/summary").json()
    assert summary["training_count"] == summary["unestimated_training_count"] == 1
    assert Decimal(summary["person_hours"]) == 0
    assert summary["costs"] == []


def test_status_change_preserves_training_values_and_rejects_stale_updates(
    client, task, training_data
):
    moved = client.put(
        f"/api/tasks/{task['id']}/status", json={"status": "in_progress", "version": 1}
    )
    assert moved.status_code == 200
    assert moved.json()["status"] == "in_progress"
    assert moved.json()["version"] == 2
    assert Decimal(moved.json()["person_hours"]) == Decimal("15")
    stale = client.put(
        f"/api/tasks/{task['id']}",
        json={**training_data, "title": "Устаревшее изменение", "version": 1},
    )
    assert stale.status_code == 409
    assert client.delete(f"/api/tasks/{task['id']}?version=1").status_code == 409
    assert client.get(f"/api/tasks/{task['id']}").json()["title"] == training_data["title"]
    completed = client.put(f"/api/tasks/{task['id']}/status", json={"status": "done", "version": 2})
    assert completed.status_code == 200
    assert client.get("/api/tasks?status=done").json()["total"] == 1
    assert client.get("/api/tasks?status=todo").json()["total"] == 0


def test_same_status_does_not_add_events_or_increment_version(client, task):
    before = client.get("/api/dashboard").json()["activities"]
    response = client.put(f"/api/tasks/{task['id']}/status", json={"status": "todo", "version": 1})
    assert response.json()["version"] == 1
    assert client.get("/api/dashboard").json()["activities"] == before


def test_update_recomputes_effort_and_can_change_training_to_ordinary(client, task, training_data):
    updated = client.put(
        f"/api/tasks/{task['id']}",
        json={**training_data, "duration_hours": "2.25", "participant_count": 12, "version": 1},
    )
    assert updated.status_code == 200
    assert Decimal(updated.json()["person_hours"]) == 27
    ordinary = client.put(
        f"/api/tasks/{task['id']}",
        json={"title": "Обычная задача", "version": updated.json()["version"]},
    )
    assert ordinary.status_code == 200
    assert ordinary.json()["person_hours"] is None
    assert ordinary.json()["departments"] == []


def test_multidepartment_filter_does_not_double_count(client, training_data, department):
    other = client.post("/api/departments", json={"name": "Дизайн"}).json()
    task = client.post(
        "/api/tasks", json={**training_data, "department_ids": [department["id"], other["id"]]}
    ).json()
    for department_id in (department["id"], other["id"]):
        items = client.get("/api/tasks", params={"department_id": department_id}).json()
        assert items["total"] == len(items["items"]) == 1
        assert len(items["items"][0]["departments"]) == 2
        summary = client.get("/api/tasks/summary", params={"department_id": department_id}).json()
        assert summary["total"] == 1
        assert Decimal(summary["person_hours"]) == 15
    assert client.delete(f"/api/departments/{other['id']}").status_code == 409
    assert client.delete(f"/api/tasks/{task['id']}?version=1").status_code == 204
    assert client.delete(f"/api/departments/{other['id']}").status_code == 204


def test_filters_unicode_and_pagination(client, task, training_data):
    client.post(
        "/api/tasks",
        json={
            **training_data,
            "title": "Внешний курс",
            "learning_source": "external",
            "learning_format": "individual",
            "participant_count": 1,
            "status": "done",
        },
    )
    client.post("/api/tasks", json={"title": "Подготовить план"})
    filters = [
        ({"q": "ОБУЧЕНИЕ"}, 1),
        ({"q": "%"}, 0),
        ({"q": "_"}, 0),
        ({"learning_source": "external"}, 1),
        ({"learning_format": "group"}, 1),
        ({"is_training": "true"}, 2),
        ({"is_training": "false"}, 1),
        ({"learning_source": "internal", "learning_format": "individual"}, 0),
    ]
    for params, expected in filters:
        assert client.get("/api/tasks", params=params).json()["total"] == expected
        assert client.get("/api/tasks/summary", params=params).json()["total"] == expected
    first = client.get("/api/tasks?page=1&page_size=2").json()
    second = client.get("/api/tasks?page=2&page_size=2").json()
    assert first["total"] == second["total"] == 3
    assert len(first["items"]) == 2 and len(second["items"]) == 1
    assert {t["id"] for t in first["items"]}.isdisjoint({t["id"] for t in second["items"]})


def test_summary_separates_currencies_and_free_from_unknown_cost(client, training_data):
    for data in [
        training_data,
        {**training_data, "cost": "0.10"},
        {**training_data, "cost": "10", "currency": "USD"},
        {**training_data, "cost": "0", "currency": "GBP"},
        {"title": "Нет оценки бюджета"},
    ]:
        assert client.post("/api/tasks", json=data).status_code == 201
    summary = client.get("/api/tasks/summary").json()
    totals = {item["currency"]: Decimal(item["amount"]) for item in summary["costs"]}
    assert totals == {"EUR": Decimal("123.55"), "USD": Decimal("10"), "GBP": Decimal("0")}
    assert summary["without_cost_count"] == 1
    assert Decimal(summary["person_hours"]) == 60


@pytest.mark.parametrize(
    "changes",
    [
        {"title": "  "},
        {"status": "invalid"},
        {"duration_hours": "-1"},
        {"duration_hours": "0"},
        {"duration_hours": "1.125"},
        {"duration_hours": "NaN"},
        {"cost": "1.001"},
        {"cost": "-1"},
        {"currency": None},
        {"cost": None},
        {"participant_count": 0},
        {"participant_count": True},
        {"participant_count": 1},
        {"learning_format": "individual"},
        {"learning_source": None},
        {"department_ids": [1, 1]},
        {"department_ids": [-1]},
        {"due_on": "2026-02-31"},
    ],
)
def test_training_validation(client, training_data, changes):
    assert client.post("/api/tasks", json={**training_data, **changes}).status_code == 422


def test_unknown_department_is_atomic(client, training_data):
    before = client.get("/api/dashboard").json()["activities"]
    response = client.post("/api/tasks", json={**training_data, "department_ids": [999]})
    assert response.status_code == 404
    assert client.get("/api/tasks").json()["total"] == 0
    assert client.get("/api/dashboard").json()["activities"] == before


def test_orm_version_guard_handles_concurrent_sessions(client, task):
    engine = build_engine(get_settings().database_url)
    with Session(engine) as first, Session(engine) as second:
        record_one = first.get(Task, task["id"])
        record_two = second.get(Task, task["id"])
        record_one.status = "in_progress"
        commit(first, "Conflict")
        record_two.status = "done"
        with pytest.raises(ConflictError):
            commit(second, "Conflict")
        assert second.scalar(select(Task.status).where(Task.id == task["id"])) == "in_progress"
    engine.dispose()


def test_delete_task_removes_associations_and_keeps_other_entities(client, task, department):
    assert client.delete(f"/api/tasks/{task['id']}?version=1").status_code == 204
    assert client.get(f"/api/tasks/{task['id']}").status_code == 404
    assert client.get("/api/tasks/summary").json()["total"] == 0
    assert client.get("/api/departments").json()[0]["id"] == department["id"]


@pytest.mark.parametrize(
    "url",
    [
        "/api/tasks/999",
        "/api/tasks?page=0",
        "/api/tasks?page_size=101",
        "/api/tasks?status=unknown",
    ],
)
def test_missing_task_and_invalid_query(client, url):
    assert client.get(url).status_code in (404, 422)
