"""Finite migration and pipeline checks in a uniquely named disposable PostgreSQL DB.

Uses DATABASE_URL's server/credentials with CREATE DATABASE permission. The configured
application database is never migrated, seeded, or dropped by this script.
"""
import asyncio
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import BACKEND_DIR, settings
from app.db.base import Base
import app.models


async def check_pipeline(url):
    from app.services.digitization_service import DigitizationService
    from app.services.document_service import DocumentService
    from app.services.extraction.tesseract_provider import TesseractOCRProvider
    from app.services.storage_service import LocalStorageService
    from app.services.user_service import user_service
    from app.services.report_service import verification_report_service
    from app.services.job_service import JobService
    from app.schemas.user import UserCreate

    engine = create_async_engine(url.set(drivername="postgresql+asyncpg"))
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        with tempfile.TemporaryDirectory(prefix="sih_audit_uploads_") as directory:
            storage = LocalStorageService(directory)
            pipeline = DigitizationService(storage=storage, doc_service=DocumentService(storage),
                                           extraction_provider=TesseractOCRProvider())
            async with maker() as session:
                user = await user_service.create_user(session, UserCreate(
                    email="audit@example.com", full_name="Audit User", role="ADMIN", password="AuditOnly123!"
                ))
                fixture = BACKEND_DIR / "tests/fixtures/sample_documents/clean_land_record.png"
                result = await pipeline.upload_and_process(session, fixture.name, "image/png", fixture.read_bytes())
                await session.commit()
                assert result.extraction.provider == "TESSERACT_OCR_V1"
                assert result.validations[0].is_valid
                pdf, _ = await verification_report_service.generate_verification_pdf(session, result.records[0].id, user)
                assert pdf.startswith(b"%PDF")
                # Competing enqueue transactions must serialize on the document row.
                document_id = result.document.id
            jobs = JobService(session_maker=maker)
            async def enqueue():
                from app.core.exceptions import DuplicateProcessingError
                async with maker() as session:
                    try:
                        await jobs.create_job(session, document_id)
                        await session.commit()
                        return "queued"
                    except DuplicateProcessingError:
                        return "duplicate"
            assert sorted(await asyncio.gather(enqueue(), enqueue())) == ["duplicate", "queued"]
            print("PASS: real Tesseract -> asyncpg persistence -> PDF; concurrent enqueue isolation")
    finally:
        await engine.dispose()


def main():
    source = make_url(settings.DATABASE_URL)
    if source.get_backend_name() != "postgresql":
        raise RuntimeError("DATABASE_URL must point to PostgreSQL")
    name = "sih_audit_" + uuid.uuid4().hex
    url = source.set(drivername="postgresql+psycopg2", database=name)
    admin = create_engine(source.set(drivername="postgresql+psycopg2", database="postgres"),
                          isolation_level="AUTOCOMMIT")
    created = False
    engine = None
    try:
        with admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
        created = True
        engine = create_engine(url)
        cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False).replace("%", "%%"))
        command.upgrade(cfg, "head")
        command.upgrade(cfg, "head")
        with engine.connect() as conn:
            differences = compare_metadata(MigrationContext.configure(conn), Base.metadata)
            assert not differences, differences
            assert str(inspect(conn).get_columns("alembic_version")[0]["type"]) == "TEXT"
        print("PASS: zero -> head, repeat upgrade, schema/model comparison, TEXT version column")

        for width in (32, 128):
            command.downgrade(cfg, "002_phase4_auth_audit_review")
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR({width})"))
            command.upgrade(cfg, "head")
        command.downgrade(cfg, "003_phase5_extraction_discrepancies")
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")
        with engine.begin() as conn:
            assert set(inspect(conn).get_table_names()) <= {"alembic_version"}
            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
        output = io.StringIO()
        cfg.output_buffer = output
        command.upgrade(cfg, "head", sql=True)
        assert "version_num TEXT" in output.getvalue()
        with engine.begin() as conn:
            conn.exec_driver_sql(output.getvalue())
        print("PASS: legacy VARCHAR(32)/VARCHAR(128) upgrade, long-ID downgrade, base downgrade, offline SQL replay")

        env = os.environ.copy()
        env.update(DATABASE_URL=url.set(drivername="postgresql+asyncpg").render_as_string(hide_password=False), APP_ENV="development")
        for _ in range(2):
            subprocess.run([sys.executable, "scripts/seed_demo_data.py"], cwd=BACKEND_DIR, env=env, check=True, timeout=60)
        asyncio.run(check_pipeline(url))
        subprocess.run([sys.executable, "scripts/seed_cadastral_parcels.py"], cwd=BACKEND_DIR, env=env, check=True, timeout=60)
        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM users")).scalar_one() == 5
            assert conn.execute(text("SELECT map_source FROM parcel_locations")).scalar_one() == "DEMO_SYNTHETIC"
        print("PASS: idempotent user seeds and synthetic parcel seed through application services")
    finally:
        if engine is not None:
            engine.dispose()
        if created:
            # Only the random database created by this invocation is removed.
            with admin.connect() as conn:
                conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
            print("Disposable audit database removed.")
        admin.dispose()


if __name__ == "__main__":
    main()
