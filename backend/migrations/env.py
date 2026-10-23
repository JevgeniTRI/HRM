from alembic import context

from app import models  # noqa: F401
from app.config import get_settings
from app.database import Base, build_engine
from app.tasks import models as task_models  # noqa: F401

config = context.config
target_metadata = Base.metadata
url = get_settings().database_url

if context.is_offline_mode():
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = build_engine(url)
    with engine.connect() as connection:
        sqlite = connection.dialect.name == "sqlite"
        if sqlite:
            # Batch migrations rebuild referenced tables. Suspend FK checks on this connection
            # only, and explicitly begin so SQLite DDL participates in the transaction.
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
            connection.exec_driver_sql("BEGIN")
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            transactional_ddl=True,
        )
        try:
            with context.begin_transaction():
                context.run_migrations()
                if sqlite and connection.exec_driver_sql("PRAGMA foreign_key_check").first():
                    raise RuntimeError("Migration would leave invalid foreign key relationships")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            if sqlite:
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                connection.commit()
