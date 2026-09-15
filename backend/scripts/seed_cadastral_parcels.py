"""
SIH26018 Intelligent Land Record Digitization and Validation System
Cadastral Parcel Seeding Script for Hackathon Demonstration
Generates realistic parcel polygon boundaries and coordinates for existing land records.
"""

import sys
import os
import asyncio
import uuid
from datetime import datetime

# Ensure backend root is on Python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.models.land_record import LandRecordModel
from app.models.parcel_location import ParcelLocationModel
from app.models.user import UserModel
from app.schemas.gis import ParcelLocationBase
from app.services.gis_service import gis_service
from scripts.seed_support import check_seed_environment, require_migrations

def generate_parcel_polygon(center_lat: float, center_lon: float, offset: float = 0.003):
    """Generates a closed GeoJSON polygon ring around a centroid."""
    half = offset / 2.0
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [round(center_lon - half, 5), round(center_lat - half, 5)],
                [round(center_lon + half, 5), round(center_lat - half, 5)],
                [round(center_lon + half, 5), round(center_lat + half, 5)],
                [round(center_lon - half, 5), round(center_lat + half, 5)],
                [round(center_lon - half, 5), round(center_lat - half, 5)],
            ]
        ]
    }

async def seed_parcels():
    check_seed_environment()
    print("Connecting to configured database...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Base locations for different districts
    district_coords = {
        "jaipur": (26.8530, 75.8040),
        "bhopal": (23.2599, 77.4126),
        "sanganer": (26.8120, 75.7780),
        "huzur": (23.2800, 77.4300),
    }

    try:
        async with session_factory() as session:
            await require_migrations(session)
            admin = (await session.execute(select(UserModel).where(UserModel.role == "ADMIN", UserModel.is_active.is_(True)).limit(1))).scalar_one_or_none()
            if admin is None:
                raise RuntimeError("Seed an active demo admin first.")
            # 1. Fetch records
            result = await session.execute(select(LandRecordModel))
            records = list(result.scalars().all())

            if not records:
                print("No land records found. Please ingest or seed documents/records first.")
                return

            print(f"Found {len(records)} land records. Checking parcel locations...")
            seeded_count = 0

            for i, rec in enumerate(records):
                # Check if parcel location already exists
                loc_check = await session.execute(
                    select(ParcelLocationModel).where(ParcelLocationModel.record_id == rec.id)
                )
                existing_loc = loc_check.scalar_one_or_none()

                if existing_loc:
                    continue

                # Determine centroid based on district or village
                dist_key = (rec.district or "").lower()
                tehsil_key = (rec.tehsil or "").lower()
                base_lat, base_lon = district_coords.get(dist_key, district_coords.get(tehsil_key, (26.8500, 75.8000)))

                # Jitter slightly for each parcel so they cluster naturally as adjacent cadastral plots
                jitter_lat = base_lat + (i * 0.0035)
                jitter_lon = base_lon + ((i % 3) * 0.004)

                polygon = generate_parcel_polygon(jitter_lat, jitter_lon, offset=0.003)

                await gis_service.attach_parcel_location(
                    session, rec.id,
                    ParcelLocationBase(
                        latitude=jitter_lat,
                        longitude=jitter_lon,
                        boundary_geojson=polygon,
                        map_source="DEMO_SYNTHETIC",
                        location_confidence=0.0,
                    ),
                    admin,
                )
                seeded_count += 1

            await session.commit()
            print(f"Successfully attached cadastral spatial boundaries to {seeded_count} land records!")

    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_parcels())
