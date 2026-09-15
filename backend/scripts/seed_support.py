"""Guards shared by development seed scripts; never creates application tables."""
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from app.core.config import BACKEND_DIR, settings


def check_seed_environment():
    if settings.APP_ENV.lower() != "development":
        raise RuntimeError("Demo seeds may only run with APP_ENV=development")


async def require_migrations(session):
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    expected = set(ScriptDirectory.from_config(config).get_heads())
    connection = await session.connection()
    actual = await connection.run_sync(
        lambda conn: set(MigrationContext.configure(conn).get_current_heads())
    )
    if actual != expected:
        raise RuntimeError("Database is not at Alembic head. Run python -m alembic upgrade head first.")
