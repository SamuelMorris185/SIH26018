"""
SIH26018 Intelligent Land Record Digitization and Validation System
Automated Hackathon Demo Preparation Script (backend/scripts/prepare_demo.py)

Responsibilities:
1. Verifies database connectivity.
2. Verifies Alembic schema is at HEAD (exits clearly if not).
3. Safely seeds/verifies the 4 demo users (ADMIN, OPERATOR, REVIEWER, VIEWER).
4. Safely seeds/verifies cadastral parcel spatial coordinates for any existing land records.
5. Strictly IDEMPOTENT: running repeatedly creates zero duplicates.
6. Strictly adheres to Alembic schema ownership: NEVER calls Base.metadata.create_all().
"""

import sys
import os
import asyncio
import uuid
from typing import Dict, Any

# Ensure backend root is in search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, text
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory

from app.core.config import BACKEND_DIR, settings
from app.models.user import UserModel
from app.models.land_record import LandRecordModel
from app.models.parcel_location import ParcelLocationModel
from app.schemas.user import UserCreate
from app.schemas.gis import ParcelLocationBase
from app.services.user_service import user_service
from app.services.gis_service import gis_service
from scripts.seed_demo_data import DEMO_USERS
from scripts.seed_cadastral_parcels import generate_parcel_polygon
from scripts.seed_support import check_seed_environment

DISTRICT_COORDS = {
    "jaipur": (26.8530, 75.8040),
    "bhopal": (23.2599, 77.4126),
    "sanganer": (26.8120, 75.7780),
    "huzur": (23.2800, 77.4300),
}


async def verify_alembic_head(session) -> str:
    """Verifies that the target database is at the latest Alembic revision."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    expected_heads = set(ScriptDirectory.from_config(config).get_heads())
    connection = await session.connection()
    current_heads = await connection.run_sync(
        lambda conn: set(MigrationContext.configure(conn).get_current_heads())
    )

    if current_heads != expected_heads:
        head_str = ", ".join(expected_heads) if expected_heads else "None"
        curr_str = ", ".join(current_heads) if current_heads else "None"
        print(f"\n[ERROR] Database schema mismatch!")
        print(f"        Expected Alembic HEAD: {head_str}")
        print(f"        Current Database HEAD:  {curr_str}")
        print("\nPlease apply migrations before preparing demo data:")
        print("  .\\venv\\Scripts\\python.exe -m alembic upgrade head\n")
        sys.exit(1)

    return ", ".join(expected_heads)


async def prepare_demo():
    print("=" * 70)
    print("SIH26018 - DEMO ENVIRONMENT PREPARATION")
    print("=" * 70)

    check_seed_environment()

    # 1. Connectivity Check
    print(f"\n[1/4] Checking PostgreSQL database connectivity...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    stats: Dict[str, Dict[str, int]] = {
        "users": {"created": 0, "already_present": 0, "updated": 0, "skipped": 0},
        "parcels": {"created": 0, "already_present": 0, "updated": 0, "skipped": 0},
    }

    try:
        async with session_factory() as session:
            try:
                res = await session.execute(text("SELECT 1"))
                assert res.scalar() == 1
                print("      Database connection established successfully.")
            except Exception as e:
                print(f"[ERROR] Could not connect to database at {settings.DATABASE_URL}: {e}")
                sys.exit(1)

            # 2. Alembic HEAD Verification
            print(f"\n[2/4] Verifying Alembic migration status...")
            active_rev = await verify_alembic_head(session)
            print(f"      Schema verified at Alembic HEAD: {active_rev}")

            # 3. Seed Demo Users (Idempotent)
            print(f"\n[3/4] Verifying / Seeding Hackathon Demo Accounts...")
            for u in DEMO_USERS:
                stmt = select(UserModel).where(UserModel.email == u["email"])
                existing = (await session.execute(stmt)).scalars().first()

                if existing:
                    print(f"      [ALREADY PRESENT] {u['role']:<9} : {u['email']}")
                    stats["users"]["already_present"] += 1
                else:
                    await user_service.create_user(
                        session,
                        UserCreate(
                            email=u["email"],
                            password=u["password"],
                            full_name=u["full_name"],
                            role=u["role"],
                        ),
                    )
                    print(f"      [CREATED]         {u['role']:<9} : {u['email']}")
                    stats["users"]["created"] += 1

            await session.commit()

            # 4. Seed Cadastral Parcels for existing land records (Idempotent)
            print(f"\n[4/4] Verifying / Seeding Cadastral GIS Parcel Boundaries...")
            admin_user = (
                await session.execute(
                    select(UserModel).where(UserModel.role == "ADMIN", UserModel.is_active.is_(True)).limit(1)
                )
            ).scalar_one_or_none()

            rec_stmt = select(LandRecordModel)
            records = list((await session.execute(rec_stmt)).scalars().all())

            if not records:
                print("      [SKIPPED] No land records exist yet in the database.")
                print("                Cadastral parcel polygons will automatically bind upon document ingestion.")
                stats["parcels"]["skipped"] += 1
            else:
                for i, rec in enumerate(records):
                    loc_stmt = select(ParcelLocationModel).where(ParcelLocationModel.record_id == rec.id)
                    existing_loc = (await session.execute(loc_stmt)).scalar_one_or_none()

                    if existing_loc:
                        print(f"      [ALREADY PRESENT] Parcel for Record {rec.id} (Khasra: {rec.khasra_number or 'N/A'})")
                        stats["parcels"]["already_present"] += 1
                    else:
                        dist_key = (rec.district or "").lower()
                        tehsil_key = (rec.tehsil or "").lower()
                        base_lat, base_lon = DISTRICT_COORDS.get(
                            dist_key, DISTRICT_COORDS.get(tehsil_key, (23.2599, 77.4126))
                        )
                        jitter_lat = base_lat + (i * 0.0035)
                        jitter_lon = base_lon + ((i % 3) * 0.004)
                        polygon = generate_parcel_polygon(jitter_lat, jitter_lon, offset=0.003)

                        await gis_service.attach_parcel_location(
                            session=session,
                            record_id=rec.id,
                            location_data=ParcelLocationBase(
                                latitude=jitter_lat,
                                longitude=jitter_lon,
                                boundary_geojson=polygon,
                                map_source="DEMO_SYNTHETIC",
                                location_confidence=0.95,
                            ),
                            current_user=admin_user,
                        )
                        print(f"      [CREATED]         Parcel for Record {rec.id} (Khasra: {rec.khasra_number or 'N/A'})")
                        stats["parcels"]["created"] += 1

                await session.commit()

        print("\n" + "=" * 70)
        print("DEMO PREPARATION SUMMARY")
        print("=" * 70)
        print(f"  Demo Users  : Created: {stats['users']['created']}, Already Present: {stats['users']['already_present']}, Updated: {stats['users']['updated']}, Skipped: {stats['users']['skipped']}")
        print(f"  GIS Parcels : Created: {stats['parcels']['created']}, Already Present: {stats['parcels']['already_present']}, Updated: {stats['parcels']['updated']}, Skipped: {stats['parcels']['skipped']}")
        print(f"  Alembic Rev : {active_rev} (HEAD)")
        print("\nStatus: DEMO ENVIRONMENT IS READY FOR EVALUATION!")
        print("=" * 70 + "\n")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(prepare_demo())
