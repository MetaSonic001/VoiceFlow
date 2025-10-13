from minio import Minio
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

_RAW_MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
# Support either MINIO_ACCESS_KEY / MINIO_SECRET_KEY or MINIO_ROOT_USER / MINIO_ROOT_PASSWORD
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY') or os.getenv('MINIO_ROOT_USER') or 'minioadmin'
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY') or os.getenv('MINIO_ROOT_PASSWORD') or 'minioadmin'
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'voiceflow')


def _normalize_endpoint(raw: str):
    """Accept either 'host:port' or 'http(s)://host:port' and return (hostport, secure).

    Examples:
      'localhost:9000' -> ('localhost:9000', False)
      'http://localhost:9000' -> ('localhost:9000', False)
      'https://example.com:9000' -> ('example.com:9000', True)
    """
    if not raw:
        return 'localhost:9000', False
    parsed = urlparse(raw)
    if parsed.scheme and parsed.hostname:
        host = parsed.hostname
        port = parsed.port
        hostport = f"{host}:{port}" if port else host
        secure = parsed.scheme.lower() == 'https'
        return hostport, secure
    # no scheme; assume host:port
    secure_env = os.getenv('MINIO_SECURE', 'false').lower() in ('1', 'true', 'yes')
    return raw, secure_env


def get_minio_client():
    endpoint, secure_flag = _normalize_endpoint(_RAW_MINIO_ENDPOINT)
    return Minio(
        endpoint,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=secure_flag,
    )


def ensure_bucket(client=None):
    c = client or get_minio_client()
    try:
        found = c.bucket_exists(MINIO_BUCKET)
        if not found:
            c.make_bucket(MINIO_BUCKET)
        return True
    except Exception:
        # If MinIO is not reachable or credentials are wrong, return False
        return False


def upload_file(fileobj, dest_path: str, client=None):
    c = client or get_minio_client()
    ensure_bucket(c)
    # fileobj should be a file-like object supporting read()
    c.put_object(MINIO_BUCKET, dest_path, fileobj, length=-1, part_size=10*1024*1024)
    return f"s3://{MINIO_BUCKET}/{dest_path}"
