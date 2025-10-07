from minio import Minio
import os
from dotenv import load_dotenv

load_dotenv()

MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'voiceflow')


def get_minio_client():
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=os.getenv('MINIO_SECURE', 'false').lower() in ('1','true','yes')
    )


def ensure_bucket(client=None):
    c = client or get_minio_client()
    found = c.bucket_exists(MINIO_BUCKET)
    if not found:
        c.make_bucket(MINIO_BUCKET)


def upload_file(fileobj, dest_path: str, client=None):
    c = client or get_minio_client()
    ensure_bucket(c)
    # fileobj should be a file-like object supporting read()
    c.put_object(MINIO_BUCKET, dest_path, fileobj, length=-1, part_size=10*1024*1024)
    return f"s3://{MINIO_BUCKET}/{dest_path}"
