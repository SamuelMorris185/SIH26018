import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import Text, inspect, text
from sqlalchemy.engine import make_url

from alembic import context
from alembic.ddl.postgresql import PostgresqlImpl


class LandRecordPostgresqlImpl(PostgresqlImpl):
    """Keep published revision IDs intact, including the 33-character revision 003."""

    __dialect__ = "postgresql"

    def version_table_impl(self, **kwargs):
        table = super().version_table_impl(**kwargs)
        table.c.version_num.type = Text()
        return table

# Ensure backend root is on sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core.config import settings
from app.db.base import Base
# Import all models to register on Base.metadata
from app.models import (
    UserModel,
    DocumentModel,
    LandRecordModel,
    ExtractionResultModel,
    ValidationResultModel,
    AuditLogModel,
    RecordComparisonModel,
    DiscrepancyModel,
    JobModel,
    ParcelLocationModel
)


config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    x_args = context.get_x_argument(as_dictionary=True)
    url = make_url(x_args.get("url") or config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL)
    if url.drivername in {"postgresql", "postgresql+asyncpg"}:
        url = url.set(drivername="postgresql+psycopg2")
    return url.render_as_string(hide_password=False)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.begin() as connection:
        # Existing databases may have Alembic's original VARCHAR(32), or a
        # manually widened column. TEXT preserves all values and never narrows it.
        if connection.dialect.name == "postgresql" and inspect(connection).has_table("alembic_version"):
            column = next(c for c in inspect(connection).get_columns("alembic_version") if c["name"] == "version_num")
            if getattr(column["type"], "length", None) is not None:
                connection.execute(text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE TEXT"))
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
