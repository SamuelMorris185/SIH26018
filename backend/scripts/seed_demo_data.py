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
from app.core.security import get_password_hash
from app.models.user import UserModel
from app.db.base import Base

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
    print(f"Connecting to database: {settings.DATABASE_URL}...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            for u in DEMO_USERS:
                stmt = select(UserModel).where(UserModel.email == u["email"])
                res = await session.execute(stmt)
                existing = res.scalars().first()

                if existing:
                    existing.hashed_password = get_password_hash(u["password"])
                    existing.role = u["role"]
                    existing.full_name = u["full_name"]
                    existing.is_active = True
                    print(f"  [UPDATED] {u['role']}: {u['email']} / {u['password']}")
                else:
                    user = UserModel(
                        id=u["id"],
                        email=u["email"],
                        hashed_password=get_password_hash(u["password"]),
                        full_name=u["full_name"],
                        role=u["role"],
                        is_active=True,
                        created_at=datetime.utcnow(),
                    )
                    session.add(user)
                    print(f"  [CREATED] {u['role']}: {u['email']} / {u['password']}")

            await session.commit()
            print("\nDemo users successfully seeded!")
    except Exception as e:
        print(f"\nCould not connect to database ({settings.DATABASE_URL}): {e}")
        print("Note: To run live with PostgreSQL, start PostgreSQL daemon or container on port 5432.")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_users())
