"""Create all SQLAlchemy tables (idempotent — skips existing ones)."""
import asyncio

from app.column_patches import apply_column_patches
from app.database import engine
from app.models import Base


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await apply_column_patches(engine)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
