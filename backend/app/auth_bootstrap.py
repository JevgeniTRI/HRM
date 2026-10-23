"""Local-only creation of the first administrator: python -m app.auth_bootstrap."""

import secrets

from sqlalchemy import select

from app.auth import password_hash
from app.database import SessionLocal
from app.models import Account


def bootstrap():
    with SessionLocal() as session:
        if session.scalar(select(Account.id).limit(1)) is not None:
            print("Accounts already exist; use the administrator interface.")
            return
        password = secrets.token_urlsafe(18)
        session.add(
            Account(
                username="admin",
                password_hash=password_hash(password),
                role="admin",
                is_active=True,
            )
        )
        session.commit()
        print(f"Administrator created.\nUsername: admin\nPassword: {password}")


if __name__ == "__main__":
    bootstrap()
