"""
SIH26018 Intelligent Land Record Digitization and Validation System
Database Seeding Script for Hackathon Demonstration Users
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
from app.models.user import UserModel
from app.schemas.user import UserCreate
from app.services.user_service import user_service
from scripts.seed_support import check_seed_environment, require_migrations

DEMO_USERS = [
    {
        "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "email": "admin@revenue.gov.in",
        "password": "AdminPass123!",
        "full_name": "Chief Revenue Commissioner (Admin)",
        "role": "ADMIN",
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "email": "operator_demo@revenue.gov.in",
        "password": "OperatorDemoPass123!",
        "full_name": "Revenue Patwari (Operator)",
        "role": "OPERATOR",
    },
    {
        "id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
        "email": "reviewer_demo@revenue.gov.in",
        "password": "ReviewerDemoPass123!",
        "full_name": "Sub-Divisional Magistrate (Reviewer)",
        "role": "REVIEWER",
    },
    {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444444"),
        "email": "viewer_demo@revenue.gov.in",
        "password": "ViewerDemoPass123!",
        "full_name": "Citizen Applicant (Viewer)",
        "role": "VIEWER",
    },
]

async def seed_users():
    check_seed_environment()
    print("Connecting to configured database...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            await require_migrations(session)
            for u in DEMO_USERS:
                stmt = select(UserModel).where(UserModel.email == u["email"])
                res = await session.execute(stmt)
                existing = res.scalars().first()

                if existing:
                    print(f"  [EXISTS] {u['email']} (unchanged)")
                else:
                    await user_service.create_user(session, UserCreate(
                        email=u["email"],
                        password=u["password"],
                        full_name=u["full_name"],
                        role=u["role"],
                    ))
                    print(f"  [CREATED] {u['role']}: {u['email']}")

            await session.commit()
            print("\nDemo users successfully seeded!")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_users())
