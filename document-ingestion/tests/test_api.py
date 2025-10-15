"""
Comprehensive tests for the Document Ingestion FastAPI
Tests all routes, data formats, and error handling
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import UploadFile
import io
import json
from unittest.mock import patch, AsyncMock
import asyncio
import os

# Set environment variables to suppress warnings
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Import the FastAPI app
from main import app

client = TestClient(app)


class TestDocumentIngestionAPI:
    """Test suite for Document Ingestion API"""

    def test_root_endpoint(self):
        """Test root endpoint returns API information"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "Document Ingestion API" in data["name"]
        assert "endpoints" in data

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data

    @patch('services.database.DatabaseManager.check_connection')
    @patch('services.vector_store.VectorStore.check_connection')
    @patch('services.ocr_processor.OCRProcessor.is_available')
    @patch('services.web_scraper.WebScraper.is_available')
    def test_health_check_services(self, mock_scraper, mock_ocr, mock_vector, mock_db):
        """Test health check with mocked services"""
        mock_db.return_value = True
        mock_vector.return_value = True
        mock_ocr.return_value = True
        mock_scraper.return_value = True

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert all(data["services"].values())

    def test_ingest_file_missing_tenant_agent(self):
        """Test file ingestion without tenant_id and agent_id"""
        # Create a test file
        test_content = b"Test document content"
        files = {"file": ("test.txt", io.BytesIO(test_content), "text/plain")}

        response = client.post("/ingest", files=files)
        # Should fail because tenant_id and agent_id are required
        assert response.status_code == 422  # Validation error

    def test_ingest_file_valid(self):
        """Test file ingestion with valid data"""
        test_content = b"Test document content"
        files = {"file": ("test.txt", io.BytesIO(test_content), "text/plain")}
        data = {
            "tenant_id": "test-tenant-123",
            "agent_id": "test-agent-456"
        }

        with patch('main.process_document', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {
                "status": "success",
                "message": "Document processed successfully",
                "document_id": "test-doc-123",
                "chunks_created": 5,
                "processing_time": 1.23
            }

            response = client.post("/ingest", files=files, data=data)
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"
            assert "document_id" in result

            # Verify process_document was called with correct args
            mock_process.assert_called_once()
            call_args = mock_process.call_args
            assert call_args[1]["tenant_id"] == "test-tenant-123"
            assert call_args[1]["agent_id"] == "test-agent-456"

    def test_ingest_url_missing_tenant_agent(self):
        """Test URL ingestion without tenant_id and agent_id"""
        url_data = {
            "url": "https://example.com/document.pdf"
        }

        response = client.post("/ingest/url", json=url_data)
        assert response.status_code == 422  # Validation error

    def test_ingest_url_valid(self):
        """Test URL ingestion with valid data"""
        url_data = {
            "url": "https://example.com/document.pdf",
            "tenant_id": "test-tenant-123",
            "agent_id": "test-agent-456",
            "metadata": {"source": "web"}
        }

        with patch('main.process_document', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {
                "status": "success",
                "message": "URL processed successfully",
                "document_id": "test-url-doc-123",
                "chunks_created": 10,
                "processing_time": 2.45
            }

            response = client.post("/ingest/url", json=url_data)
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"
            assert result["document_id"] == "test-url-doc-123"

    def test_ingest_onboarding_info_valid(self):
        """Test onboarding info ingestion with valid data"""
        onboarding_data = {
            "tenant_id": "test-tenant-123",
            "agent_id": "test-agent-456",
            "company_name": "Acme Corporation",
            "industry": "Technology",
            "primary_use_case": "Customer Support",
            "brief_description": "A leading tech company",
            "agent_name": "Sarah",
            "agent_role": "Customer Support Specialist",
            "agent_description": "Helpful and patient assistant",
            "communication_channels": ["phone", "chat", "email"],
            "metadata": {"source": "onboarding"}
        }

        with patch('main.process_document', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {
                "status": "success",
                "message": "Onboarding info processed successfully",
                "document_id": "onboarding-doc-123",
                "chunks_created": 3,
                "processing_time": 1.0
            }

            response = client.post("/ingest/onboarding-info", json=onboarding_data)
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"
            assert result["document_id"] == "onboarding-doc-123"

            # Verify process_document was called
            mock_process.assert_called_once()

    def test_ingest_url_invalid_url(self):
        """Test URL ingestion with invalid URL"""
        url_data = {
            "url": "",
            "tenant_id": "test-tenant-123",
            "agent_id": "test-agent-456"
        }

        response = client.post("/ingest/url", json=url_data)
        assert response.status_code == 400
        assert "URL cannot be blank" in response.json()["detail"]

    def test_get_document_not_found(self):
        """Test getting non-existent document"""
        with patch('services.database.DatabaseManager.get_document', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            response = client.get("/documents/non-existent-id")
            assert response.status_code == 404
            assert "Document not found" in response.json()["detail"]

    def test_get_document_success(self):
        """Test getting existing document"""
        mock_doc = {
            "id": "test-doc-123",
            "filename": "test.pdf",
            "file_type": "pdf",
            "metadata": {"tenant_id": "tenant-123"},
            "created_at": "2023-01-01T00:00:00",
            "status": "completed"
        }

        with patch('services.database.DatabaseManager.get_document', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_doc

            response = client.get("/documents/test-doc-123")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["document"]["id"] == "test-doc-123"

    def test_search_documents(self):
        """Test document search"""
        with patch('services.embedder.TextEmbedder.embed_text', new_callable=AsyncMock) as mock_embed:
            with patch('services.vector_store.VectorStore.search', new_callable=AsyncMock) as mock_search:
                mock_embed.return_value = [0.1, 0.2, 0.3]  # Mock embedding
                mock_search.return_value = [
                    {
                        "document_id": "doc-1",
                        "chunk_text": "Sample text",
                        "score": 0.95
                    }
                ]

                response = client.get("/search?query=test%20query")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert "results" in data

    def test_delete_document_not_found(self):
        """Test deleting non-existent document"""
        with patch('services.database.DatabaseManager.get_document', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            response = client.delete("/documents/non-existent-id")
            assert response.status_code == 404
            assert "Document not found" in response.json()["message"]

    def test_delete_document_success(self):
        """Test deleting existing document"""
        mock_doc = {"id": "test-doc-123", "filename": "test.pdf"}

        with patch('services.database.DatabaseManager.get_document', new_callable=AsyncMock) as mock_get:
            with patch('services.database.DatabaseManager.delete_document', new_callable=AsyncMock) as mock_delete:
                with patch('services.vector_store.VectorStore.delete_embeddings_by_document', new_callable=AsyncMock) as mock_vector_delete:
                    mock_get.return_value = mock_doc

                    response = client.delete("/documents/test-doc-123")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "success"
                    assert data["document_id"] == "test-doc-123"

    def test_bulk_delete_documents(self):
        """Test bulk delete functionality"""
        bulk_data = {
            "document_ids": ["doc-1", "doc-2", "doc-3"]
        }

        with patch('services.database.DatabaseManager.get_document', new_callable=AsyncMock) as mock_get:
            with patch('services.database.DatabaseManager.delete_document', new_callable=AsyncMock) as mock_delete:
                with patch('services.vector_store.VectorStore.delete_embeddings_by_document', new_callable=AsyncMock) as mock_vector_delete:
                    # Mock get_document to return a doc for existing ones
                    mock_get.return_value = {"id": "doc-1", "filename": "test.pdf"}

                    response = client.post("/documents/bulk-delete", json=bulk_data)
                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] in ["success", "partial"]
                    assert "deleted" in data
                    assert "not_found" in data
                    assert "errors" in data

    def test_list_documents(self):
        """Test listing documents with pagination"""
        mock_docs = [
            {"id": "doc-1", "filename": "test1.pdf"},
            {"id": "doc-2", "filename": "test2.pdf"}
        ]

        with patch('services.database.DatabaseManager.list_documents', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = (mock_docs, 2)

            response = client.get("/documents?limit=10&offset=0")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert len(data["documents"]) == 2
            assert data["total"] == 2

    def test_get_document_embeddings(self):
        """Test getting document embeddings info"""
        with patch('services.vector_store.VectorStore.get_by_document_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {
                    "id": "chunk-1",
                    "metadata": {"chunk_index": 0, "total_chunks": 5},
                    "document": "Sample chunk text"
                }
            ]

            response = client.get("/documents/test-doc-123/embeddings")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["document_id"] == "test-doc-123"
            assert "embeddings_count" in data
            assert "sample" in data

    def test_webhook_upload(self):
        """Test webhook upload endpoint"""
        test_content = b"Webhook test content"
        files = {"file": ("webhook.txt", io.BytesIO(test_content), "text/plain")}
        data = {
            "tenant_id": "webhook-tenant",
            "agent_id": "webhook-agent"
        }

        with patch('main.process_document', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {
                "status": "success",
                "message": "Webhook upload successful",
                "document_id": "webhook-doc-123"
            }

            response = client.post("/webhook/upload", files=files, data=data)
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"

    def test_admin_sync(self):
        """Test admin sync endpoint"""
        with patch('services.vector_store.VectorStore.sync_from_database', new_callable=AsyncMock) as mock_sync:
            response = client.post("/admin/sync")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "Sync started" in data["message"]


class TestDataFormats:
    """Test various data formats and edge cases"""

    def test_pdf_upload(self):
        """Test PDF file upload"""
        # Mock PDF content (just bytes)
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        data = {"tenant_id": "tenant-123", "agent_id": "agent-456"}

        with patch('main.process_document', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {"status": "success", "document_id": "pdf-doc-123"}

            response = client.post("/ingest", files=files, data=data)
            assert response.status_code == 200

    def test_image_upload(self):
        """Test image file upload"""
        # Mock minimal PNG content
        png_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        files = {"file": ("test.png", io.BytesIO(png_content), "image/png")}
        data = {"tenant_id": "tenant-123", "agent_id": "agent-456"}

        with patch('main.process_document', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {"status": "success", "document_id": "img-doc-123"}

            response = client.post("/ingest", files=files, data=data)
            assert response.status_code == 200

    def test_text_file_with_url(self):
        """Test text file containing URL gets processed as URL"""
        url_content = b"https://example.com/document.html"
        files = {"file": ("url.txt", io.BytesIO(url_content), "text/plain")}
        data = {"tenant_id": "tenant-123", "agent_id": "agent-456"}

        with patch('main.process_document', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {"status": "success", "document_id": "url-doc-123"}

            response = client.post("/ingest", files=files, data=data)
            assert response.status_code == 200

            # Verify it was processed as URL
            call_args = mock_process.call_args
            assert call_args[1]["file_type"] == "url"

    def test_large_file_handling(self):
        """Test handling of large files"""
        large_content = b"x" * (10 * 1024 * 1024)  # 10MB
        files = {"file": ("large.txt", io.BytesIO(large_content), "text/plain")}
        data = {"tenant_id": "tenant-123", "agent_id": "agent-456"}

        with patch('main.process_document', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {"status": "success", "document_id": "large-doc-123"}

            response = client.post("/ingest", files=files, data=data)
            assert response.status_code == 200

    def test_malformed_request(self):
        """Test handling of malformed requests"""
        # Missing file
        data = {"tenant_id": "tenant-123", "agent_id": "agent-456"}
        response = client.post("/ingest", data=data)
        assert response.status_code == 422

        # Invalid JSON for URL endpoint
        response = client.post("/ingest/url", data="invalid json")
        assert response.status_code == 422


class TestErrorHandling:
    """Test error handling scenarios"""

    def test_processing_error(self):
        """Test handling of processing errors"""
        test_content = b"Test content"
        files = {"file": ("test.txt", io.BytesIO(test_content), "text/plain")}
        data = {"tenant_id": "tenant-123", "agent_id": "agent-456"}

        with patch('main.process_document', new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = Exception("Processing failed")

            response = client.post("/ingest", files=files, data=data)
            assert response.status_code == 500
            assert "Processing error" in response.json()["detail"]

    def test_database_connection_error(self):
        """Test database connection errors"""
        with patch('services.database.DatabaseManager.check_connection', return_value=False):
            response = client.get("/health")
            data = response.json()
            assert data["status"] == "degraded"
            assert not data["services"]["database"]

    def test_vector_store_error(self):
        """Test vector store errors"""
        with patch('services.vector_store.VectorStore.check_connection', return_value=False):
            response = client.get("/health")
            data = response.json()
            assert data["status"] == "degraded"
            assert not data["services"]["vector_store"]


if __name__ == "__main__":
    pytest.main([__file__])