import json

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
    command.upgrade(config, "0007")
    with engine.begin() as connection:
        connection.execute(
            text("""
            INSERT INTO certificates
                (id, employee_skill_id, title, original_name, stored_name,
                 content_type, size, created_at)
            VALUES (1, 1, 'Certificate', 'cert.pdf', 'stored.pdf', 'application/pdf', 5,
                    '2026-09-01 00:00:00')
        """)
        )
    command.upgrade(config, "0008")
    requirements = {"0": "Нет опыта", "1": "Создаёт таблицу", "3": "Строит отчёты\nОбучает коллег"}
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE skills SET level_descriptions=:value"), {"value": json.dumps(requirements)}
        )
    command.upgrade(config, "0009")
    with engine.begin() as connection:
        connection.execute(
            text("""
            INSERT INTO accounts
                (id, username, password_hash, role, employee_id, is_active)
            VALUES (1, 'manager', 'unused-migration-test', 'manager', 1, 1)
        """)
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT current_level FROM employee_skills")).scalar() == 3
        assert connection.execute(text("SELECT target_level FROM employee_skills")).scalar() == 4
        assert connection.execute(text("SELECT employee_skill_id FROM certificates")).scalar() == 1
        assert connection.execute(text("SELECT scale_type FROM skills")).scalar() == "numeric"
        assert connection.execute(text("SELECT scale_min, scale_max FROM skills")).one() == (0, 5)
        assert (
            json.loads(connection.execute(text("SELECT level_descriptions FROM skills")).scalar())
            == requirements
        )
        assert (
            json.loads(connection.execute(text("SELECT level_names FROM skills")).scalar())["2"]
            == "Базовый"
        )
        assert connection.execute(text("SELECT employee_id FROM activities")).scalar() == 1
        assert connection.execute(text("SELECT is_manager, manager_id FROM employees")).one() == (
            0,
            None,
        )
        assert connection.execute(text("SELECT employee_id, role FROM accounts")).one() == (
            1,
            "employee",
        )
        assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert connection.execute(
            text(
                "SELECT photo_stored_name, photo_content_type, photo_size, photo_version "
                "FROM employees"
            )
        ).one() == (None, None, None, 0)
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("UPDATE employees SET status='invalid' WHERE id=1"))
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("UPDATE employees SET manager_id=id WHERE id=1"))
    engine.dispose()
    get_settings.cache_clear()


def test_department_hierarchy_upgrade_keeps_valid_chain_and_normalizes_access(
    tmp_path, monkeypatch
):
    url = f"sqlite:///{(tmp_path / 'departments.db').as_posix()}"
    monkeypatch.setenv("HRM_DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "0010")
    engine = build_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO departments VALUES (1, 'A', 'a', ''), (2, 'B', 'b', '')")
        )
        for person, department, parent in ((1, 1, None), (2, 1, 1), (3, 1, 2), (4, 2, 1)):
            connection.execute(
                text("""
                INSERT INTO employees
                    (id, first_name, last_name, email, position, search_text,
                     department_id, status, hired_at, created_at, is_manager, manager_id)
                VALUES (:id, 'Test', 'Person', :email, 'Engineer', 'test person',
                        :department, 'active', '2026-01-01', '2026-01-01', 1, :parent)
            """),
                {
                    "id": person,
                    "email": f"{person}@example.com",
                    "department": department,
                    "parent": parent,
                },
            )
        for account, person, role in (
            (1, 1, "manager"),
            (2, 2, "manager"),
            (3, 3, "manager"),
            (4, 4, "power_user"),
        ):
            connection.execute(
                text("""
                INSERT INTO accounts (id, username, password_hash, role, employee_id, is_active)
                VALUES (:id, :username, 'unused-test', :role, :person, 1)
            """),
                {"id": account, "username": f"account-{account}", "person": person, "role": role},
            )
            connection.execute(
                text("""
                INSERT INTO auth_sessions (token_hash, account_id, expires_at)
                VALUES (:token, :account, '2099-01-01')
            """),
                {"token": f"token-{account}", "account": account},
            )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT id, manager_id, is_manager FROM employees ORDER BY id")
        ).all() == [
            (1, None, 1),
            (2, 1, 1),
            (3, 2, 0),
            (4, None, 0),
        ]
        assert connection.execute(
            text("SELECT role FROM accounts ORDER BY id")
        ).scalars().all() == [
            "manager",
            "manager",
            "employee",
            "power_user",
        ]
        assert connection.execute(
            text("SELECT account_id FROM auth_sessions ORDER BY account_id")
        ).scalars().all() == [1, 2, 4]
        assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
    engine.dispose()
    get_settings.cache_clear()
