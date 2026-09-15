"""Compatibility entry point for the migrated development-user seed."""
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from scripts.seed_demo_data import seed_users

if __name__ == "__main__":
    asyncio.run(seed_users())
