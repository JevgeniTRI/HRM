import pytest


def save_scale(client, skill, kind, minimum, maximum, descriptions=None):
    return client.put(
        f"/api/skills/{skill['id']}",
        json={
            **skill,
            "scale": {
                "type": kind,
                "min": minimum,
                "max": maximum,
                "descriptions": descriptions or {},
            },
        },
    )


def test_existing_default_scale_and_legacy_update_preserve_descriptions(client, skill):
    assert skill["scale"]["min"] == 0
    assert skill["scale"]["max"] == 5
    assert skill["scale"]["names"]["2"] == "Базовый"
    assert skill["scale"]["descriptions"] == {}
    assert save_scale(client, skill, "numeric", 0, 10, {"10": "Ведёт обучение"}).status_code == 200
    changed = client.put(
        f"/api/skills/{skill['id']}",
        json={"name": "Python 3", "category": skill["category"], "description": "Описание навыка"},
    )
    assert changed.status_code == 200
    assert changed.json()["scale"]["max"] == 10
    assert changed.json()["scale"]["descriptions"] == {"10": "Ведёт обучение"}


@pytest.mark.parametrize("kind,maximum", [("numeric", 10), ("letter", 25)])
def test_level_names_and_requirements_persist_separately(client, employee, kind, maximum):
    scale = {
        "type": kind,
        "min": 0,
        "max": maximum,
        "names": {"0": "Нет опыта", "2": "Базовый", str(maximum): "Эксперт"},
        "descriptions": {
            "0": "Не работал с инструментом",
            "2": "Создаёт таблицы\nИспользует формулы",
            str(maximum): "Автоматизирует отчёты",
        },
    }
    response = client.post(
        "/api/skills", json={"name": "Excel", "category": "Tech", "scale": scale}
    )
    assert response.status_code == 201, response.text
    skill = response.json()
    path = f"/api/employees/{employee['id']}/skills/{skill['id']}"
    assert client.put(path, json={"current_level": 2, "target_level": maximum}).status_code == 200
    profile = client.get(f"/api/employees/{employee['id']}").json()["skills"][0]["skill"]
    assert profile["scale"]["names"]["2"] == "Базовый"
    assert profile["scale"]["descriptions"]["2"] == "Создаёт таблицы\nИспользует формулы"
    assert client.get("/api/matrix").json()["skills"][0] == profile
    assert client.get("/api/dashboard").json()["skill_metrics"][0]["scale"] == profile["scale"]
    # Old clients that omit names must keep the custom titles on update.
    scale.pop("names")
    scale["descriptions"]["2"] = "Умеет строить диаграммы"
    changed = client.put(f"/api/skills/{skill['id']}", json={**skill, "scale": scale})
    assert changed.status_code == 200
    assert changed.json()["scale"]["names"][str(maximum)] == "Эксперт"
    assert changed.json()["scale"]["descriptions"]["2"] == "Умеет строить диаграммы"


@pytest.mark.parametrize("kind,maximum", [("numeric", 10), ("letter", 25)])
def test_scale_endpoints_and_descriptions_work_in_profile_matrix_and_dashboard(
    client, employee, skill, kind, maximum
):
    response = save_scale(
        client, skill, kind, 0, maximum, {str(maximum): "Эксперт\nОбучает команду"}
    )
    assert response.status_code == 200, response.text
    scale = response.json()["scale"]
    path = f"/api/employees/{employee['id']}/skills/{skill['id']}"
    for current, target, state in (
        (0, 0, "met"),
        (0, maximum, "gap"),
        (maximum, maximum, "met"),
        (None, maximum, "unassessed"),
    ):
        response = client.put(path, json={"current_level": current, "target_level": target})
        assert response.status_code == 200, response.text
        assert response.json()["state"] == state
        assert response.json()["skill"]["scale"] == scale
    profile = client.get(f"/api/employees/{employee['id']}").json()
    matrix = client.get("/api/matrix").json()
    metric = client.get("/api/dashboard").json()["skill_metrics"][0]
    assert profile["skills"] == matrix["employees"][0]["skills"]
    assert matrix["skills"][0]["scale"] == metric["scale"] == scale
    assert metric["average_level"] is None


@pytest.mark.parametrize("kind,minimum,maximum", [("numeric", 2, 7), ("letter", 2, 7)])
def test_assessments_must_match_the_individual_skill_range(
    client, employee, skill, kind, minimum, maximum
):
    assert save_scale(client, skill, kind, minimum, maximum).status_code == 200
    path = f"/api/employees/{employee['id']}/skills/{skill['id']}"
    for current, target in (
        (minimum - 1, maximum),
        (maximum + 1, maximum),
        (None, minimum - 1),
        (minimum, maximum + 1),
    ):
        response = client.put(path, json={"current_level": current, "target_level": target})
        assert response.status_code == 422, response.text
    assert (
        client.put(path, json={"current_level": minimum, "target_level": maximum}).status_code
        == 200
    )


@pytest.mark.parametrize(
    "current,target,minimum,maximum", [(0, 4, 1, 5), (5, 3, 0, 4), (None, 5, 0, 4)]
)
def test_narrowing_range_cannot_discard_existing_scores_or_targets(
    client, employee, skill, current, target, minimum, maximum
):
    path = f"/api/employees/{employee['id']}/skills/{skill['id']}"
    assert (
        client.put(path, json={"current_level": current, "target_level": target}).status_code == 200
    )
    before = client.get(f"/api/employees/{employee['id']}").json()["skills"][0]
    response = save_scale(client, skill, "numeric", minimum, maximum)
    assert response.status_code == 409
    assert "исключает существующие оценки" in response.json()["detail"]
    assert client.get(f"/api/employees/{employee['id']}").json()["skills"][0] == before
    assert client.get("/api/skills").json()[0]["scale"] == skill["scale"]


def test_switching_to_letters_preserves_scores_and_activity_uses_letters(client, employee, skill):
    path = f"/api/employees/{employee['id']}/skills/{skill['id']}"
    client.put(path, json={"current_level": 2, "target_level": 4})
    changed = save_scale(client, skill, "letter", 0, 25, {"2": "Самостоятельная работа"})
    assert changed.status_code == 200
    assessment = client.get(f"/api/employees/{employee['id']}").json()["skills"][0]
    assert assessment["current_level"] == 2 and assessment["target_level"] == 4
    client.put(path, json={"current_level": 25, "target_level": 25})
    activity = client.get("/api/dashboard").json()["activities"][0]
    assert ": Z, цель Z" in activity["detail"]


@pytest.mark.parametrize(
    "scale",
    [
        {"type": "numeric", "min": 0, "max": 11},
        {"type": "letter", "min": 0, "max": 26},
        {"type": "numeric", "min": -1, "max": 10},
        {"type": "letter", "min": 5, "max": 4},
        {"type": "other", "min": 0, "max": 5},
        {"type": "numeric", "min": 0, "max": 10, "descriptions": {"11": "Недопустимый уровень"}},
        {"type": "numeric", "min": 0, "max": 10, "descriptions": {"1": "x" * 1001}},
        {"type": "numeric", "min": False, "max": 10},
        {"type": "numeric", "min": 0, "max": 10, "names": {"11": "Вне диапазона"}},
        {"type": "numeric", "min": 0, "max": 10, "names": {"1": "x" * 101}},
    ],
)
def test_invalid_scale_configuration_is_rejected(client, scale):
    response = client.post("/api/skills", json={"name": "Test", "category": "Tech", "scale": scale})
    assert response.status_code == 422, response.text
    assert client.get("/api/skills").json() == []
