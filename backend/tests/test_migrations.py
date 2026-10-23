import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.database import build_engine


def test_populated_upgrade_keeps_assessments_and_relationships(tmp_path, monkeypatch):
    """Table rebuilds must retain data, not cascade-delete it with SQLite foreign keys enabled."""
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setenv("HRM_DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "0001")
    engine = build_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO departments VALUES (1, 'Team', 'team', '')"))
        connection.execute(text("INSERT INTO skills VALUES (1, 'Python', 'python', 'Tech', '')"))
        connection.execute(
            text("""
            INSERT INTO employees VALUES
            (1, 'Test', 'Person', 'test@example.com', 'Engineer', 'test person',
            1, 'active', '2026-09-01', '2026-09-01 00:00:00')
        """)
        )
        connection.execute(
            text("""
            INSERT INTO employee_skills VALUES (1, 1, 1, 3, 4, '2026-09-01 00:00:00')
        """)
        )
        connection.execute(
            text("""
            INSERT INTO activities VALUES (1, 'employee', 'Created', 'Person', 1,
            '2026-09-01 00:00:00')
        """)
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT current_level FROM employee_skills")).scalar() == 3
        assert connection.execute(text("SELECT employee_id FROM activities")).scalar() == 1
        assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("UPDATE employees SET status='invalid' WHERE id=1"))
    engine.dispose()
    get_settings.cache_clear()
