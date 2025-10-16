import asyncio
import sys
import pathlib
import uuid
import io


async def main():
    # Ensure repository root and document-ingestion are importable
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    ingestion_path = repo_root / 'document-ingestion'
    if str(ingestion_path) not in sys.path and ingestion_path.exists():
        sys.path.insert(0, str(ingestion_path))

    # Import ingestion DB manager
    from services.database import DatabaseManager

    dbm = DatabaseManager()

    # Create a small document via ingestion DB manager
    content = b"This is a test document for DB unification."
    document_id = await dbm.store_document("unify_test.txt", content, "text", {"source": "test"})
    print(f"Stored ingestion document id: {document_id}")

    # Verify we can read it back
    doc = await dbm.get_document(document_id)
    print("Ingestion get_document ->", bool(doc), "id=", doc.get('id') if doc else None)

    # Now ensure backend DB can reference this document id
    # Import backend DB session and models
    try:
        from backend.backend.db import AsyncSessionLocal
        from backend.backend.models import Document
    except Exception as e:
        print(f"Failed to import backend DB/session: {e}")
        return

    async with AsyncSessionLocal() as session:
        # Create a backend Document row referencing the ingestion id
        backend_doc = Document(
            id=document_id,
            agent_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            filename='unify_test.txt',
            file_path=f'tenants/test/assets/{document_id}',
            file_type='text'
        )
        session.add(backend_doc)
        await session.commit()
        await session.refresh(backend_doc)
        print(f"Inserted backend document with id: {backend_doc.id}")

        # Fetch it back
        fetched = await session.get(Document, document_id)
        print("Backend fetch ->", bool(fetched), "id=", fetched.id if fetched else None)


if __name__ == '__main__':
    asyncio.run(main())
