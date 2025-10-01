"""
OCR Processing Service using docTR
Handles image and PDF OCR
"""

from doctr.io import DocumentFile
from doctr.models import ocr_predictor
import numpy as np
from PIL import Image
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    Service for OCR processing using docTR
    """
    
    def __init__(self):
        try:
            # Initialize docTR model
            logger.info("Initializing docTR OCR model...")
            self.model = ocr_predictor(pretrained=True)
            logger.info("docTR OCR model initialized successfully")
            self._available = True
        except Exception as e:
            logger.error(f"Failed to initialize OCR model: {e}", exc_info=True)
            self._available = False
            self.model = None
    
    def is_available(self) -> bool:
        """Check if OCR service is available"""
        return self._available
    
    async def process(self, content: bytes, file_type: str) -> str:
        """
        Process image or PDF with OCR
        
        Args:
            content: File content as bytes
            file_type: 'image' or 'pdf'
        
        Returns:
            Extracted text
        """
        if not self._available:
            raise Exception("OCR service is not available")
        
        logger.info(f"Starting OCR processing for {file_type}")
        
        try:
            if file_type == "image":
                return await self._process_image(content)
            elif file_type == "pdf":
                return await self._process_pdf(content)
            else:
                raise ValueError(f"Unsupported file type for OCR: {file_type}")
        
        except Exception as e:
            logger.error(f"OCR processing error: {e}", exc_info=True)
            raise
    
    async def _process_image(self, content: bytes) -> str:
        """
        Process a single image
        
        Args:
            content: Image content as bytes
        
        Returns:
            Extracted text
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(content))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            logger.info(f"Image size: {image.size}")
            
            # Convert to numpy array
            img_array = np.array(image)
            
            # Run OCR
            logger.info("Running OCR on image...")
            result = self.model([img_array])
            
            # Extract text from result
            text = self._extract_text_from_result(result)
            
            logger.info(f"OCR extracted {len(text)} characters from image")
            return text
        
        except Exception as e:
            logger.error(f"Image OCR error: {e}", exc_info=True)
            raise
    
    async def _process_pdf(self, content: bytes) -> str:
        """
        Process PDF with OCR
        
        Args:
            content: PDF content as bytes
        
        Returns:
            Extracted text from all pages
        """
        try:
            # Save to temporary file for docTR
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            
            logger.info(f"Processing PDF from temporary file: {tmp_path}")
            
            # Load PDF with docTR
            doc = DocumentFile.from_pdf(tmp_path)
            logger.info(f"PDF loaded with {len(doc)} pages")
            
            # Run OCR on all pages
            logger.info("Running OCR on PDF pages...")
            result = self.model(doc)
            
            # Extract text
            text = self._extract_text_from_result(result)
            
            # Clean up temporary file
            import os
            os.unlink(tmp_path)
            
            logger.info(f"OCR extracted {len(text)} characters from PDF")
            return text
        
        except Exception as e:
            logger.error(f"PDF OCR error: {e}", exc_info=True)
            raise
    
    def _extract_text_from_result(self, result) -> str:
        """
        Extract text from docTR result object
        
        Args:
            result: docTR OCR result
        
        Returns:
            Extracted text as string
        """
        try:
            text_lines = []
            
            # Navigate docTR result structure
            for page in result.pages:
                for block in page.blocks:
                    for line in block.lines:
                        line_text = " ".join([word.value for word in line.words])
                        if line_text.strip():
                            text_lines.append(line_text)
            
            # Join all lines
            full_text = "\n".join(text_lines)
            
            return full_text
        
        except Exception as e:
            logger.error(f"Text extraction error: {e}", exc_info=True)
            # Fallback: try to export as text
            try:
                return result.export()
            except:
                return ""