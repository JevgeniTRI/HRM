"""Disposable seeded database for browser tests; never touches the workspace database."""

import os
import tempfile
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config

backend_dir = Path(__file__).resolve().parents[1]
os.chdir(backend_dir)
artifacts = backend_dir.parent / "artifacts"
artifacts.mkdir(exist_ok=True)

with tempfile.TemporaryDirectory(prefix="hrm-e2e-", dir=artifacts) as temporary:
    os.environ["HRM_DATABASE_URL"] = f"sqlite:///{Path(temporary).as_posix()}/hrm.db"
    os.environ["HRM_MEDIA_ROOT"] = str(Path(temporary) / "media")
    os.environ["HRM_CORS_ORIGINS"] = '["http://127.0.0.1:5174", "http://127.0.0.1:8001"]'
    # App imports happen after configuring the isolated database.
    command.upgrade(Config("alembic.ini"), "head")
    from app.seed import seed
    from app.tasks.seed import seed_tasks

    seed()
    seed_tasks()
    from app.auth import password_hash
    from app.database import SessionLocal
    from app.models import Account

    with SessionLocal() as session:
        session.add(
            Account(
                username="admin",
                password_hash=password_hash("E2e-admin-password-2026"),
                role="admin",
                is_active=True,
            )
        )
        session.commit()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001)
