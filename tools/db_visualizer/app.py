from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import os
import json
import pathlib
import sqlite3
from pathlib import Path

# Try to load .env from the visualizer folder or repo root so users can create a simple .env file
try:
    from dotenv import load_dotenv
    env_candidates = [Path(__file__).parent / '.env', Path(__file__).resolve().parents[2] / '.env']
    for p in env_candidates:
        if p.exists():
            load_dotenv(dotenv_path=str(p))
            break
except Exception:
    # python-dotenv is optional; if it's not installed the app will still work but env vars must be set externally
    pass


def _normalize_endpoint(e: str):
    """Ensure endpoint has a scheme. boto3 expects endpoint_url like http://host:port"""
    if not e:
        return e
    e = str(e).strip()
    # already has scheme
    if e.startswith('http://') or e.startswith('https://'):
        return e
    # also allow ws:// or other schemas, but default to http
    return 'http://' + e

app = FastAPI(title="DB Visualizer")


@app.get("/", response_class=HTMLResponse)
def index():
    static = pathlib.Path(__file__).parent / 'static' / 'index.html'
    if not static.exists():
        return HTMLResponse("<h1>DB Visualizer</h1><p>No UI installed.</p>")
    return HTMLResponse(static.read_text())


def _repo_root():
    # repo root (assume tools/ is under repo root)
    return pathlib.Path(__file__).resolve().parents[3]


@app.get("/api/chroma")
def inspect_chroma():
    repo = _repo_root()
    candidates = [
        repo / 'document-ingestion' / 'chroma_db' / 'chroma.sqlite3',
        repo / 'document-ingestion' / 'chroma_db' / 'chroma.sqlite',
        repo / 'document-ingestion' / 'chroma.sqlite3',
    ]
    found = []
    details = []
    for c in candidates:
        if c.exists():
            found.append(str(c))
            # attempt to read sqlite schema and simple table row counts
            try:
                conn = sqlite3.connect(str(c))
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in cur.fetchall()]
                tinfo = {}
                for t in tables:
                    try:
                        cur.execute(f"SELECT count(*) FROM '{t}'")
                        cnt = cur.fetchone()[0]
                    except Exception:
                        cnt = None
                    tinfo[t] = cnt
                details.append({"path": str(c), "tables": tinfo})
                conn.close()
            except Exception as e:
                details.append({"path": str(c), "error": str(e)})
    return JSONResponse({"found": found, "details": details})


@app.get("/api/minio")
def inspect_minio():
    endpoint = _normalize_endpoint(os.getenv('MINIO_ENDPOINT') or os.getenv('MINIO_URL') or os.getenv('MINIO_HOST'))
    access = os.getenv('MINIO_ACCESS_KEY') or os.getenv('MINIO_KEY')
    secret = os.getenv('MINIO_SECRET_KEY') or os.getenv('MINIO_SECRET')
    preview = {"endpoint": endpoint, "has_credentials": bool(access and secret)}
    # optional: list buckets if boto3 available and creds set
    if endpoint and access and secret:
        try:
            import boto3
            from botocore.client import Config
            s3 = boto3.resource('s3', endpoint_url=endpoint, aws_access_key_id=access, aws_secret_access_key=secret, config=Config(signature_version='s3v4'))
            buckets = [b.name for b in s3.buckets.all()]
            preview['buckets'] = buckets
            # sample first bucket's first 10 objects
            if buckets:
                sample = []
                bucket = s3.Bucket(buckets[0])
                for i, obj in enumerate(bucket.objects.limit(10)):
                    sample.append({'key': obj.key, 'size': obj.size})
                    if i >= 9:
                        break
                preview['sample_objects'] = sample
        except Exception as e:
            preview['error'] = str(e)
    return JSONResponse(preview)


@app.get('/api/minio/objects')
def list_minio_objects(bucket: str = None, prefix: str = None, limit: int = 50, marker: str = None):
    endpoint = _normalize_endpoint(os.getenv('MINIO_ENDPOINT') or os.getenv('MINIO_URL') or os.getenv('MINIO_HOST'))
    access = os.getenv('MINIO_ACCESS_KEY') or os.getenv('MINIO_KEY')
    secret = os.getenv('MINIO_SECRET_KEY') or os.getenv('MINIO_SECRET')
    if not (endpoint and access and secret):
        return JSONResponse({'error': 'MinIO endpoint or credentials not set in env'})
    try:
        import boto3
        from botocore.client import Config
        s3 = boto3.resource('s3', endpoint_url=endpoint, aws_access_key_id=access, aws_secret_access_key=secret, config=Config(signature_version='s3v4'))
        buckets = [b.name for b in s3.buckets.all()]
        if not bucket:
            return JSONResponse({'buckets': buckets})
        if bucket not in buckets:
            return JSONResponse({'error': f'bucket {bucket} not found', 'buckets': buckets})
        objs = []
        i = 0
        for obj in s3.Bucket(bucket).objects.filter(Prefix=prefix or ''):
            objs.append({'key': obj.key, 'size': obj.size, 'last_modified': str(obj.last_modified)})
            i += 1
            if i >= limit:
                break
        return JSONResponse({'bucket': bucket, 'objects': objs})
    except Exception as e:
        return JSONResponse({'error': str(e)})


@app.get("/api/postgres")
def inspect_postgres():
    # Prefer BACKEND_DATABASE_URL (project variable), fall back to common env names
    dburl = os.getenv('BACKEND_DATABASE_URL') or os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL') or os.getenv('PG_URI')
    if not dburl:
        return JSONResponse({"database_url": None, "error": "No DATABASE_URL/POSTGRES_URL/PG_URI found in environment"})
    # optional: try SQLAlchemy to list tables and sample rows
    try:
        from sqlalchemy import create_engine, inspect, text
        # If the URL uses asyncpg (postgresql+asyncpg), SQLAlchemy sync engine won't accept it.
        # Create a sync-compatible URL by replacing +asyncpg -> +psycopg2 when inspecting.
        eng_url = dburl
        if '+asyncpg' in eng_url:
            eng_url = eng_url.replace('+asyncpg', '+psycopg2')
        eng = create_engine(eng_url)
        inspector = inspect(eng)
        tables = inspector.get_table_names()
        samples = {}
        with eng.connect() as conn:
            for t in tables:
                try:
                    r = conn.execute(text(f"SELECT * FROM {t} LIMIT 5"))
                    rows = [dict(row._mapping) for row in r.fetchall()]
                except Exception as e:
                    rows = {"error": str(e)}
                samples[t] = rows
        return JSONResponse({"database_url": dburl, "tables": tables, "samples": samples})
    except Exception as e:
        return JSONResponse({"database_url": dburl, "error": str(e)})


@app.get('/api/postgres/table/{table_name}')
def inspect_table(table_name: str, limit: int = 25, offset: int = 0, q: str = None):
    """Return paged rows for a table. Optional simple text search `q` will apply to all text columns (best effort)."""
    dburl = os.getenv('BACKEND_DATABASE_URL') or os.getenv('DATABASE_URL')
    if not dburl:
        return JSONResponse({'error': 'No DATABASE_URL/BACKEND_DATABASE_URL set'})
    try:
        from sqlalchemy import create_engine, inspect, text
        eng_url = dburl
        if '+asyncpg' in eng_url:
            eng_url = eng_url.replace('+asyncpg', '+psycopg2')
        eng = create_engine(eng_url)
        inspector = inspect(eng)
        tables = inspector.get_table_names()
        if table_name not in tables:
            return JSONResponse({'error': f'table {table_name} not found', 'tables': tables})
        # build query
        with eng.connect() as conn:
            if q:
                # attempt to find text columns
                cols = [c['name'] for c in inspector.get_columns(table_name) if str(c.get('type')).lower().find('char') != -1 or str(c.get('type')).lower().find('text')!=-1]
                if cols:
                    conds = ' OR '.join([f"CAST({c} AS TEXT) ILIKE :q" for c in cols])
                    sql = text(f"SELECT * FROM {table_name} WHERE {conds} LIMIT :limit OFFSET :offset")
                    rows = conn.execute(sql, {'q': f'%{q}%', 'limit': limit, 'offset': offset}).fetchall()
                else:
                    rows = []
            else:
                sql = text(f"SELECT * FROM {table_name} LIMIT :limit OFFSET :offset")
                rows = conn.execute(sql, {'limit': limit, 'offset': offset}).fetchall()
            samples = [dict(r._mapping) for r in rows]
        return JSONResponse({'table': table_name, 'rows': samples, 'limit': limit, 'offset': offset})
    except Exception as e:
        return JSONResponse({'error': str(e)})


@app.get("/api/graph")
def build_graph(limit_minio=50, limit_pg=200, limit_chroma=200):
    """Best-effort graph builder linking MinIO objects -> Postgres rows -> Chroma entries.
    Returns nodes and edges plus diagnostics. Heuristics are used; adjust limits as needed.
    """
    nodes = []
    edges = []
    diag = {"minio": None, "postgres": None, "chroma": None}

    # 1) MinIO objects
    endpoint = _normalize_endpoint(os.getenv('MINIO_ENDPOINT') or os.getenv('MINIO_URL') or os.getenv('MINIO_HOST'))
    access = os.getenv('MINIO_ACCESS_KEY') or os.getenv('MINIO_KEY')
    secret = os.getenv('MINIO_SECRET_KEY') or os.getenv('MINIO_SECRET')
    minio_objects = []
    if endpoint and access and secret:
        try:
            import boto3
            from botocore.client import Config
            s3 = boto3.resource('s3', endpoint_url=endpoint, aws_access_key_id=access, aws_secret_access_key=secret, config=Config(signature_version='s3v4'))
            buckets = [b.name for b in s3.buckets.all()]
            diag['minio'] = {'endpoint': endpoint, 'buckets': buckets}
            for bname in buckets:
                bnode_id = f"minio:bucket:{bname}"
                nodes.append({'id': bnode_id, 'type': 'minio_bucket', 'label': bname})
                cnt = 0
                for obj in s3.Bucket(bname).objects.limit(limit_minio):
                    obj_id = f"minio:obj:{bname}:{obj.key}"
                    nodes.append({'id': obj_id, 'type': 'minio_object', 'label': obj.key, 'size': obj.size, 'bucket': bname})
                    edges.append({'source': bnode_id, 'target': obj_id, 'label': 'contains'})
                    minio_objects.append({'bucket': bname, 'key': obj.key, 'id': obj_id})
                    cnt += 1
                    if cnt >= limit_minio:
                        break
        except Exception as e:
            diag['minio'] = {'error': str(e)}
    else:
        diag['minio'] = {'note': 'No MinIO creds/config found in env'}

    # 2) Postgres rows
    dburl = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL') or os.getenv('PG_URI')
    pg_rows = []
    if dburl:
        try:
            from sqlalchemy import create_engine, inspect, text
            eng = create_engine(dburl)
            inspector = inspect(eng)
            tables = inspector.get_table_names()
            diag['postgres'] = {'tables': tables}
            with eng.connect() as conn:
                for t in tables:
                    # attempt to sample rows; prefer tables with 'id' and some text columns
                    try:
                        r = conn.execute(text(f"SELECT * FROM {t} LIMIT {limit_pg}"))
                        rows = [dict(row._mapping) for row in r.fetchall()]
                        for row in rows:
                            pk = None
                            if 'id' in row:
                                pk = row.get('id')
                            else:
                                # try first column
                                pk = list(row.values())[0] if row else None
                            nid = f"pg:{t}:{pk}"
                            nodes.append({'id': nid, 'type': 'pg_row', 'table': t, 'label': str(pk), 'data': row})
                            pg_rows.append({'table': t, 'pk': pk, 'id': nid, 'data': row})
                    except Exception:
                        continue
        except Exception as e:
            diag['postgres'] = {'error': str(e)}
    else:
        diag['postgres'] = {'note': 'No DATABASE_URL found in env'}

    # 3) Chroma sqlite heuristics
    repo = _repo_root()
    chroma_paths = [
        repo / 'document-ingestion' / 'chroma_db' / 'chroma.sqlite3',
        repo / 'document-ingestion' / 'chroma_db' / 'chroma.sqlite',
        repo / 'document-ingestion' / 'chroma.sqlite3',
    ]
    chroma_entries = []
    for p in chroma_paths:
        if p.exists():
            try:
                conn = sqlite3.connect(str(p))
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in cur.fetchall()]
                diag['chroma'] = {'path': str(p), 'tables': tables}
                # look for table with document, document_id, or metadata
                for t in tables:
                    try:
                        cur.execute(f"PRAGMA table_info('{t}')")
                        cols = [r[1] for r in cur.fetchall()]
                        # heuristic: table contains 'document_id' or 'document'
                        if any(c.lower().find('document') != -1 for c in cols):
                            cur.execute(f"SELECT * FROM '{t}' LIMIT {limit_chroma}")
                            rws = cur.fetchall()
                            colnames = cols
                            for rw in rws:
                                rowd = {colnames[i]: rw[i] for i in range(len(colnames))}
                                # attempt to find document id
                                docid = rowd.get('document_id') or rowd.get('document') or rowd.get('id')
                                nid = f"chroma:{t}:{len(chroma_entries)}"
                                nodes.append({'id': nid, 'type': 'chroma_entry', 'table': t, 'label': str(docid), 'data': rowd})
                                chroma_entries.append({'table': t, 'docid': docid, 'id': nid, 'data': rowd})
                    except Exception:
                        continue
                conn.close()
            except Exception as e:
                diag['chroma'] = {'error': str(e)}
            break
    if not diag.get('chroma'):
        diag['chroma'] = {'note': 'No chroma sqlite found in common locations'}

    # Heuristics to link objects -> pg rows
    # If object key contains postgres pk or filename, link
    import re
    for obj in minio_objects:
        for row in pg_rows:
            try:
                # check if pk or any string field is in object key
                pk = str(row['pk'])
                if pk and pk in obj['key']:
                    edges.append({'source': obj['id'], 'target': row['id'], 'label': 'maybe-origin'})
                    continue
                # check filename fields in row
                for v in row['data'].values():
                    if isinstance(v, str) and v and v in obj['key']:
                        edges.append({'source': obj['id'], 'target': row['id'], 'label': 'maybe-origin'})
                        break
            except Exception:
                continue

    # Link pg rows -> chroma entries by matching docid
    for row in pg_rows:
        for cent in chroma_entries:
            try:
                if cent['docid'] and str(cent['docid']) in map(str, row['data'].values()):
                    edges.append({'source': row['id'], 'target': cent['id'], 'label': 'embeddings_for'})
            except Exception:
                continue

    return JSONResponse({'nodes': nodes, 'edges': edges, 'diag': diag})
