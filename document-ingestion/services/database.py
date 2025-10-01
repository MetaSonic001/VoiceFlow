"""
Database Service for Supabase/PostgreSQL
Handles document metadata and original file storage
"""

from supabase import create_client, Client
from typing import Dict, Any, Optional, List
import logging
import os
from datetime import datetime
import uuid
import base64

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Service for managing document storage in Supabase/PostgreSQL
    """
    
    def __init__(self):
        """
        Initialize Supabase client
        """
        try:
            # Get credentials from environment
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                logger.warning("Supabase credentials not found in environment")
                self.client = None
                return
            
            logger.info("Initializing Supabase client")
            self.client: Client = create_client(supabase_url, supabase_key)
            
            # Table name for documents
            self.table_name = "documents"
            
            logger.info("Supabase client initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize Supabase: {e}", exc_info=True)
            self.client = None
    
    async def check_connection(self) -> bool:
        """
        Check if database connection is working
        
        Returns:
            True if connected, False otherwise
        """
        if not self.client:
            return False
        
        try:
            # Simple query to test connection
            result = self.client.table(self.table_name).select("count", count="exact").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
    
    async def store_document(
        self,
        filename: str,
        content: bytes,
        file_type: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Store document metadata and content
        
        Args:
            filename: Original filename
            content: Document content as bytes
            file_type: Type of file (image, pdf, url, etc.)
            metadata: Additional metadata
        
        Returns:
            Document ID
        """
        if not self.client:
            raise Exception("Database client not initialized")
        
        document_id = str(uuid.uuid4())
        
        logger.info(f"Storing document {filename} with ID {document_id}")
        
        try:
            # Prepare document record
            document_record = {
                "id": document_id,
                "filename": filename,
                "file_type": file_type,
                "file_size": len(content),
                "content": base64.b64encode(content).decode('utf-8'),  # Store as base64
                "metadata": metadata,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "status": "processing"
            }
            
            # Insert into database
            result = self.client.table(self.table_name).insert(document_record).execute()
            
            logger.info(f"Document {document_id} stored successfully")
            
            return document_id
        
        except Exception as e:
            logger.error(f"Error storing document: {e}", exc_info=True)
            raise
    
    async def update_document_status(
        self,
        document_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update document processing status
        
        Args:
            document_id: Document ID
            status: New status (processing, completed, failed)
            error_message: Optional error message
        """
        if not self.client:
            return
        
        logger.info(f"Updating document {document_id} status to {status}")
        
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now().isoformat()
            }
            
            if error_message:
                update_data["error_message"] = error_message
            
            result = self.client.table(self.table_name).update(update_data).eq("id", document_id).execute()
            
            logger.info(f"Document status updated successfully")
        
        except Exception as e:
            logger.error(f"Error updating document status: {e}", exc_info=True)
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve document by ID
        
        Args:
            document_id: Document ID
        
        Returns:
            Document record or None
        """
        if not self.client:
            raise Exception("Database client not initialized")
        
        logger.info(f"Retrieving document {document_id}")
        
        try:
            result = self.client.table(self.table_name).select("*").eq("id", document_id).execute()
            
            if result.data and len(result.data) > 0:
                document = result.data[0]
                # Don't include base64 content in response (too large)
                if "content" in document:
                    document["has_content"] = True
                    document["content"] = None
                
                logger.info(f"Document {document_id} retrieved")
                return document
            
            logger.warning(f"Document {document_id} not found")
            return None
        
        except Exception as e:
            logger.error(f"Error retrieving document: {e}", exc_info=True)
            raise
    
    async def get_document_content(self, document_id: str) -> Optional[bytes]:
        """
        Retrieve document content
        
        Args:
            document_id: Document ID
        
        Returns:
            Document content as bytes or None
        """
        if not self.client:
            raise Exception("Database client not initialized")
        
        logger.info(f"Retrieving content for document {document_id}")
        
        try:
            result = self.client.table(self.table_name).select("content").eq("id", document_id).execute()
            
            if result.data and len(result.data) > 0:
                content_b64 = result.data[0].get("content")
                if content_b64:
                    content = base64.b64decode(content_b64)
                    logger.info(f"Content retrieved: {len(content)} bytes")
                    return content
            
            logger.warning(f"Content not found for document {document_id}")
            return None
        
        except Exception as e:
            logger.error(f"Error retrieving document content: {e}", exc_info=True)
            raise
    
    async def list_documents(self, limit: int = 10, offset: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """
        List documents with pagination
        """
        if not self.client:
            raise Exception("Database client not initialized")
        try:
            # Fetch paginated documents
            response = self.client.table(self.table_name).select("*", count="exact").range(offset, offset + limit).execute()
            documents = response.data
            total = response.count
            
            logger.info(f"Retrieved {len(documents)} documents (total: {total})")
            return documents, total
        except Exception as e:
            logger.error(f"Failed to list documents: {str(e)}")
            raise
    
        
    async def delete_document(self, document_id: str) -> None:
        """
        Delete a document record from the database by ID
        """
        if not self.client:
            raise Exception("Database client not initialized")
            
        try:
            response = self.client.table(self.table_name).delete().eq("id", document_id).execute()
            if not response.data:
                raise ValueError(f"No document found to delete: {document_id}")
            logger.info(f"Deleted document {document_id} from database")
        except Exception as e:
            logger.error(f"Failed to delete document {document_id} from database: {str(e)}")
            raise
            