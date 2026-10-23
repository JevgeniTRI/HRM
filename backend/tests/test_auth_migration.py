from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.config import get_settings
from app.database import build_engine


def test_auth_upgrade_preserves_existing_personnel_tasks_and_certificates(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'auth-upgrade.db').as_posix()}"
    monkeypatch.setenv("HRM_DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "0004")
    engine = build_engine(url)
    statements = [
        "INSERT INTO departments VALUES (1, 'Team', 'team', '')",
        "INSERT INTO skills VALUES (1, 'Python', 'python', 'Tech', '')",
        "INSERT INTO employees VALUES (1, 'Test', 'Person', 'test@example.com', "
        "'Engineer', 'test person', 1, 'active', '2026-01-01', '2026-01-01')",
        "INSERT INTO employee_skills VALUES (1, 1, 1, 3, 4, '2026-01-01')",
        "INSERT INTO certificates VALUES (1, 1, 'Diploma', 'diploma.pdf', 'file.pdf', "
        "'application/pdf', 10, '2026-01-01')",
        "INSERT INTO tasks (id, title, description, search_text, status, version, created_at, "
        "updated_at) VALUES (1, 'Existing task', '', 'existing task', 'todo', 1, "
        "'2026-01-01', '2026-01-01')",
        "INSERT INTO task_departments VALUES (1, 1)",
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT title, assignee_id FROM tasks")).one() == (
            "Existing task",
            None,
        )
        assert connection.execute(
            text("SELECT task_id, department_id FROM task_departments")
        ).one() == (1, 1)
        assert connection.execute(text("SELECT employee_skill_id FROM certificates")).scalar() == 1
        assert connection.execute(
            text("SELECT about, experience, education FROM employees")
        ).one() == ("", "", "")
        assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
    engine.dispose()
    get_settings.cache_clear()
