from decimal import Decimal


def test_moved_card_is_visible_even_when_destination_has_more_than_one_page(client):
    for index in range(22):
        response = client.post(
            "/api/tasks",
            json={
                "title": f"Old completed task {index}",
                "status": "done",
                "due_on": "2026-01-01",
            },
        )
        assert response.status_code == 201
    task = client.post("/api/tasks", json={"title": "Just moved"}).json()
    moved = client.put(f"/api/tasks/{task['id']}/status", json={"status": "done", "version": 1})
    assert moved.status_code == 200
    page = client.get("/api/tasks", params={"status": "done", "page_size": 20}).json()
    assert page["total"] == 23
    assert len(page["items"]) == 20
    assert page["items"][0]["id"] == task["id"]
    assert Decimal(client.get("/api/tasks/summary").json()["person_hours"]) == 0
