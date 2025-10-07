"""
File Type Detection Service
Detects file types and URLs
"""

import magic
import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FileDetector:
    """
    Service for detecting file types and validating URLs
    """
    
    def __init__(self):
        self.url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        logger.info("FileDetector initialized")
    
    def detect_type(self, content, filename: Optional[str] = None) -> str:
        """
        Detect file type from content and filename
        
        Args:
            content: File content as bytes
            filename: Optional filename
        
        Returns:
            File type: 'image', 'pdf', 'text', 'document', 'url'
        """
        try:
            # If a file path was passed, read a small chunk for detection
            if isinstance(content, str):
                try:
                    with open(content, 'rb') as fh:
                        sample = fh.read(1024 * 1024)
                except Exception:
                    sample = b''
                mime = magic.from_buffer(sample, mime=True)
            else:
                # Try to detect MIME type from bytes
                mime = magic.from_buffer(content, mime=True)
            logger.info(f"MIME type detected: {mime}")
            
            # Check for images
            if mime and mime.startswith('image/'):
                return 'image'
            
            # Check for PDF
            if mime == 'application/pdf' or (not isinstance(content, str) and content.startswith(b'%PDF')):
                return 'pdf'
            
            # Check for text
            if mime and mime.startswith('text/'):
                return 'text'
            
            # Check for common document types
            if mime in [
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ]:
                return 'document'
            
            # If filename provided, check extension
            if filename:
                ext = filename.lower().split('.')[-1]
                if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp']:
                    return 'image'
                if ext == 'pdf':
                    return 'pdf'
                if ext in ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']:
                    return 'document'
            
            # Default to text if small and mostly ASCII
            try:
                sample_len = len(sample) if 'sample' in locals() else len(content)
                if sample_len < 1_000_000:  # Less than 1MB
                    s = sample if 'sample' in locals() else content
                    try:
                        if not isinstance(s, str):
                            s.decode('utf-8')
                            return 'text'
                    except Exception:
                        pass
            except Exception:
                pass
            
            logger.warning(f"Unknown file type for MIME: {mime}")
            return 'unknown'
        
        except Exception as e:
            logger.error(f"Error detecting file type: {e}", exc_info=True)
            return 'unknown'
    
    def is_url(self, text: str) -> bool:
        """
        Check if text is a valid URL
        
        Args:
            text: Text to check
        
        Returns:
            True if valid URL, False otherwise
        """
        if not text or len(text.strip()) == 0:
            return False
        
        text = text.strip()
        
        # Check with regex
        if self.url_pattern.match(text):
            logger.info(f"Valid URL detected: {text}")
            return True
        
        # Check if it starts with common URL patterns
        if text.startswith(('http://', 'https://', 'www.')):
            logger.info(f"URL-like pattern detected: {text}")
            return True
        
        return False
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if URL is not blank and properly formatted
        
        Args:
            url: URL to validate
        
        Returns:
            True if valid, False otherwise
        """
        if not url or url.strip() == "":
            logger.warning("Blank URL provided")
            return False
        
        return self.is_url(url)