import pytest


@pytest.fixture
def training():
    return {
        "title": "Курс Python",
        "learning_source": "internal",
        "learning_format": "individual",
        "participant_count": 1,
        "duration_hours": "12.5",
        "start_on": "2026-10-24",
        "end_on": "2026-10-28",
    }


def test_training_period_persists_through_edit_and_status_change(client, training):
    response = client.post("/api/tasks", json=training)
    assert response.status_code == 201, response.text
    task = response.json()
    moved = client.put(
        f"/api/tasks/{task['id']}/status", json={"status": "in_progress", "version": 1}
    ).json()
    assert moved["start_on"] == "2026-10-24"
    assert moved["end_on"] == "2026-10-28"
    updated = client.put(
        f"/api/tasks/{task['id']}",
        json={**training, "end_on": "2026-11-02", "version": moved["version"]},
    )
    assert updated.status_code == 200, updated.text
    persisted = client.get(f"/api/tasks/{task['id']}").json()
    assert persisted["end_on"] == "2026-11-02"
    assert persisted["duration_hours"] == "12.5"


@pytest.mark.parametrize(
    "patch",
    [
        {"start_on": None},
        {"end_on": None},
        {"end_on": "2026-10-23"},
        {"start_on": "2026-02-30"},
        {
            "learning_source": None,
            "learning_format": None,
            "participant_count": None,
            "duration_hours": None,
        },
    ],
)
def test_invalid_training_period_is_rejected(client, training, patch):
    response = client.post("/api/tasks", json={**training, **patch})
    assert response.status_code == 422, response.text
    assert client.get("/api/tasks").json()["total"] == 0


def test_calendar_includes_overlap_boundaries_and_unscheduled_but_not_ordinary_tasks(
    client, training
):
    periods = [
        ("Crosses whole month", "2026-09-01", "2026-11-30"),
        ("Ends on first day", "2026-09-28", "2026-10-01"),
        ("One day", "2026-10-24", "2026-10-24"),
        ("Starts on last day", "2026-10-31", "2026-11-02"),
        ("Unscheduled", None, None),
        ("Before", "2026-09-01", "2026-09-30"),
        ("After", "2026-11-01", "2026-11-02"),
    ]
    for title, start, end in periods:
        response = client.post(
            "/api/tasks", json={**training, "title": title, "start_on": start, "end_on": end}
        )
        assert response.status_code == 201, response.text
    client.post("/api/tasks", json={"title": "Ordinary", "due_on": "2026-10-24"})
    params = {"from_on": "2026-10-01", "to_on": "2026-10-31", "page_size": 2}
    pages = [client.get("/api/tasks/calendar", params={**params, "page": n}) for n in (1, 2, 3)]
    assert all(response.status_code == 200 for response in pages)
    assert all(response.json()["total"] == 5 for response in pages)
    titles = [task["title"] for response in pages for task in response.json()["items"]]
    assert titles == [period[0] for period in periods[:5]]
    filtered = client.get("/api/tasks/calendar", params={**params, "q": "ONE DAY"}).json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["title"] == "One day"


def test_calendar_range_validation(client):
    assert client.get("/api/tasks/calendar").status_code == 422
    assert client.get("/api/tasks/calendar?from_on=2026-11-01&to_on=2026-10-01").status_code == 422
