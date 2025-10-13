"""Diagnostic helper for DB Visualizer
Run from the repo root with: python tools\db_visualizer\diagnose_env.py
This prints env vars the visualizer reads, tries to list MinIO buckets (if boto3 installed),
inspects Postgres tables via SQLAlchemy (if installed), and searches for Chroma sqlite files.
"""
import os
import sys
import sqlite3
from pathlib import Path


def _normalize_endpoint(e: str):
    if not e:
        return None
    e = str(e).strip()
    if e.startswith('http://') or e.startswith('https://'):
        return e
    return 'http://' + e


def print_env():
    keys = [
        'MINIO_ENDPOINT','MINIO_URL','MINIO_HOST','MINIO_ACCESS_KEY','MINIO_KEY','MINIO_SECRET_KEY','MINIO_SECRET',
        'BACKEND_DATABASE_URL','DATABASE_URL','POSTGRES_URL','PG_URI',
        'CHROMA_PERSIST_DIR'
    ]
    print('\nDetected environment variables:')
    for k in keys:
        print(f'  {k} = {os.getenv(k)!r}')


def check_minio():
    print('\nChecking MinIO...')
    endpoint = os.getenv('MINIO_ENDPOINT') or os.getenv('MINIO_URL') or os.getenv('MINIO_HOST')
    endpoint = _normalize_endpoint(endpoint)
    access = os.getenv('MINIO_ACCESS_KEY') or os.getenv('MINIO_KEY')
    secret = os.getenv('MINIO_SECRET_KEY') or os.getenv('MINIO_SECRET')
    print('  endpoint:', endpoint)
    print('  has_credentials:', bool(access and secret))
    if not (endpoint and access and secret):
        print('  Skipping boto3 check because endpoint/credentials missing')
        return
    try:
        import boto3
        from botocore.client import Config
        s3 = boto3.resource('s3', endpoint_url=endpoint, aws_access_key_id=access, aws_secret_access_key=secret, config=Config(signature_version='s3v4'))
        buckets = [b.name for b in s3.buckets.all()]
        print('  buckets:', buckets)
        if buckets:
            sample = []
            for i, obj in enumerate(s3.Bucket(buckets[0]).objects.limit(5)):
                sample.append({'key': obj.key, 'size': obj.size})
                if i >= 4: break
            print('  sample objects from first bucket:', sample)
    except Exception as e:
        print('  boto3 check failed:', repr(e))


def check_postgres():
    print('\nChecking Postgres...')
    dburl = os.getenv('BACKEND_DATABASE_URL') or os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL') or os.getenv('PG_URI')
    print('  database_url:', dburl)
    if not dburl:
        print('  No DB URL set')
        return
    try:
        from sqlalchemy import create_engine, inspect, text
        eng_url = dburl
        if '+asyncpg' in eng_url:
            eng_url = eng_url.replace('+asyncpg', '+psycopg2')
        eng = create_engine(eng_url)
        inspector = inspect(eng)
        tables = inspector.get_table_names()
        print('  tables (inspector):', tables)
        # try simple query on first table
        if tables:
            with eng.connect() as conn:
                try:
                    r = conn.execute(text(f"SELECT * FROM {tables[0]} LIMIT 3"))
                    rows = [dict(row._mapping) for row in r.fetchall()]
                    print(f'  sample rows from {tables[0]}:', rows)
                except Exception as e:
                    print('  sample query failed:', repr(e))
    except Exception as e:
        print('  SQLAlchemy check failed:', repr(e))


def check_chroma():
    print('\nChecking Chroma sqlite locations...')
    repo = Path(__file__).resolve().parents[2]
    candidates = []
    # allow CHROMA_PERSIST_DIR env var
    chroma_dir = os.getenv('CHROMA_PERSIST_DIR')
    if chroma_dir:
        candidates.append(Path(chroma_dir))
    candidates += [
        repo / 'document-ingestion' / 'chroma_db' / 'chroma.sqlite3',
        repo / 'document-ingestion' / 'chroma_db' / 'chroma.sqlite',
        repo / 'document-ingestion' / 'chroma.sqlite3',
    ]
    found = []
    for p in candidates:
        try:
            if p.exists():
                print('  found:', p)
                found.append(str(p))
                try:
                    conn = sqlite3.connect(str(p))
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [r[0] for r in cur.fetchall()]
                    print('    tables:', tables)
                    conn.close()
                except Exception as e:
                    print('    sqlite read failed:', repr(e))
        except Exception as e:
            print('  error checking', p, repr(e))
    if not found:
        print('  No chroma sqlite files found in candidates. If your Chroma persist directory is custom, set CHROMA_PERSIST_DIR env var to point to it.')


def main():
    print('\nDB Visualizer diagnostic')
    print_env()
    check_minio()
    check_postgres()
    check_chroma()


if __name__ == '__main__':
    main()
