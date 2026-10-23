import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.auth import password_hash
from app.database import build_engine, get_session
from app.main import create_app
from app.models import Account


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    monkeypatch.setenv("HRM_DATABASE_URL", url)
    monkeypatch.setenv("HRM_MEDIA_ROOT", str(tmp_path / "media"))
    monkeypatch.setenv("HRM_ALLOWED_HOSTS", '["testserver", "localhost", "127.0.0.1"]')
    from app.config import get_settings

    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    engine = build_engine(url)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add(
            Account(
                username="admin",
                password_hash=password_hash("Test-admin-password-2026"),
                role="admin",
                is_active=True,
            )
        )
        session.commit()

    def session_override():
        with factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = session_override
    with TestClient(app) as test_client:
        test_client.headers["X-HRM-Request"] = "1"
        response = test_client.post(
            "/api/auth/login", json={"username": "admin", "password": "Test-admin-password-2026"}
        )
        assert response.status_code == 200
        yield test_client
    engine.dispose()
    get_settings.cache_clear()


@pytest.fixture
def department(client):
    result = client.post("/api/departments", json={"name": "Разработка", "description": "Команда"})
    assert result.status_code == 201
    return result.json()


@pytest.fixture
def employee_data(department):
    return {
        "first_name": "Анна",
        "last_name": "Морозова",
        "email": "anna@example.com",
        "position": "Разработчик",
        "department_id": department["id"],
        "status": "active",
        "hired_at": "2026-09-01",
    }


@pytest.fixture
def employee(client, employee_data):
    result = client.post("/api/employees", json=employee_data)
    assert result.status_code == 201, result.text
    return result.json()


@pytest.fixture
def skill(client):
    result = client.post(
        "/api/skills",
        json={
            "name": "Python",
            "category": "Технические",
            "description": "Разработка сервисов",
        },
    )
    assert result.status_code == 201
    return result.json()
