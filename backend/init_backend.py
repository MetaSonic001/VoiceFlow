import asyncio
import os
from backend.backend.db import engine, Base
from backend.backend.minio_helper import get_minio_client, MINIO_BUCKET
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info('Database tables ensured')


def ensure_minio_bucket():
    client = get_minio_client()
    try:
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
            logger.info(f'Created MinIO bucket: {MINIO_BUCKET}')
        else:
            logger.info(f'Minio bucket exists: {MINIO_BUCKET}')
    except Exception as e:
        logger.exception(f'Failed to ensure MinIO bucket: {e}')


def main():
    ensure_minio_bucket()
    asyncio.run(create_tables())


if __name__ == '__main__':
    main()
