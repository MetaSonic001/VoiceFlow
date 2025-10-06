"""
OCR Processing Service using docTR
Handles image and PDF OCR
"""

from doctr.io import DocumentFile
from doctr.models import ocr_predictor
import numpy as np
from PIL import Image, ImageOps, ImageFilter
import io
import logging
from typing import Optional, List, Dict, Any
import asyncio
import concurrent.futures
import hashlib

# optional dependencies
try:
    import cv2
    _HAS_CV2 = True
except Exception:
    _HAS_CV2 = False

try:
    from pdf2image import convert_from_bytes
    _HAS_PDF2IMAGE = True
except Exception:
    _HAS_PDF2IMAGE = False

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
                # keep backward compatible: return plain text
                structured = await self.process_structured_image(content)
                return structured.get('text', '')
            elif file_type == "pdf":
                structured_pages = await self.process_structured_pdf(content)
                # concatenate page texts for compatibility
                return "\n\n".join([p.get('text', '') for p in structured_pages])
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
        # Deprecated: use process_structured_image for richer output
        structured = await self.process_structured_image(content)
        return structured.get('text', '')

    async def process_structured_image(self, content: bytes) -> Dict[str, Any]:
        """
        Process a single image and return structured OCR output:
        {
            'text': full_text,
            'blocks': [ { 'text': ..., 'bbox': [x1,y1,x2,y2] }, ... ],
            'checksum': sha256
        }
        """
        try:
            image = Image.open(io.BytesIO(content))
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Preprocess image to improve OCR accuracy
            img_pre = await asyncio.to_thread(self._preprocess_pil_image, image)
            img_array = np.array(img_pre)

            # Run docTR on single image in a thread
            result = await asyncio.to_thread(self.model, [img_array])
            structured = self._extract_structured_from_result(result)
            # add checksum
            sha = hashlib.sha256(content).hexdigest()
            structured['checksum'] = sha
            return structured
        except Exception as e:
            logger.error(f"Structured image OCR error: {e}", exc_info=True)
            raise
    
    async def _process_pdf(self, content: bytes) -> str:
        """
        Process PDF with OCR
        
        Args:
            content: PDF content as bytes
        
        Returns:
            Extracted text from all pages
        """
        # Deprecated: use process_structured_pdf to leverage page-level parallelism
        pages = await self.process_structured_pdf(content)
        return "\n\n".join([p.get('text', '') for p in pages])

    async def process_structured_pdf(self, content: bytes) -> List[Dict[str, Any]]:
        """
        Process a PDF and return a list of structured page outputs.
        This function will attempt to convert the PDF to images and OCR pages
        in parallel (using threads) to reduce total processing time.
        """
        try:
            pages_images: List[Image.Image] = []
            if _HAS_PDF2IMAGE:
                # convert all pages to PIL images
                pages_images = convert_from_bytes(content)
            else:
                # fallback: write to temp file and let docTR load (single batch)
                import tempfile, os
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                try:
                    doc = DocumentFile.from_pdf(tmp_path)
                    # extract page images from docTR DocumentFile if possible
                    for p in doc:
                        try:
                            arr = p.as_pil()
                            pages_images.append(arr)
                        except Exception:
                            pass
                finally:
                    os.unlink(tmp_path)

            if not pages_images:
                # final fallback: run model on whole PDF using docTR convenience
                import tempfile, os
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                try:
                    doc = DocumentFile.from_pdf(tmp_path)
                    result = await asyncio.to_thread(self.model, doc)
                    structured = self._extract_structured_from_result(result)
                    return [structured]
                finally:
                    os.unlink(tmp_path)

            # Process pages in parallel using a thread pool limited to CPU count
            loop = asyncio.get_event_loop()
            results: List[Dict[str, Any]] = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, max(1, len(pages_images)))) as pool:
                tasks = [loop.run_in_executor(pool, self._process_page_sync, img) for img in pages_images]
                results = await asyncio.gather(*tasks)

            return results
        except Exception as e:
            logger.error(f"Structured PDF OCR error: {e}", exc_info=True)
            raise

    def _process_page_sync(self, pil_image: Image.Image) -> Dict[str, Any]:
        """
        Synchronous helper to preprocess and OCR a single PIL image page.
        Used by the ThreadPoolExecutor to allow parallel page OCR.
        """
        try:
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            pre = self._preprocess_pil_image(pil_image)
            arr = np.array(pre)
            # run model synchronously
            result = self.model([arr])
            structured = self._extract_structured_from_result(result)
            return structured
        except Exception:
            logger.exception('Page-level OCR failed')
            return {'text': '', 'blocks': []}

    def _preprocess_pil_image(self, image: Image.Image) -> Image.Image:
        """
        Apply preprocessing: deskew (if cv2 available), binarize, contrast, and morphological ops.
        Returns a PIL Image ready for OCR.
        """
        try:
            img = image.copy()
            # convert to grayscale
            gray = img.convert('L')

            if _HAS_CV2:
                # use OpenCV for advanced preprocessing
                arr = np.array(gray)
                # deskew using moments
                coords = np.column_stack(np.where(arr > 0))
                if coords.size > 0:
                    try:
                        import cv2 as _cv
                        rect = _cv.minAreaRect(coords)
                        angle = rect[-1]
                        if angle < -45:
                            angle = -(90 + angle)
                        else:
                            angle = -angle
                        (h, w) = arr.shape[:2]
                        center = (w // 2, h // 2)
                        M = _cv.getRotationMatrix2D(center, angle, 1.0)
                        rotated = _cv.warpAffine(arr, M, (w, h), flags=_cv.INTER_CUBIC, borderMode=_cv.BORDER_REPLICATE)
                        arr = rotated
                    except Exception:
                        pass

                # adaptive threshold
                try:
                    import cv2 as _cv
                    th = _cv.adaptiveThreshold(arr, 255, _cv.ADAPTIVE_THRESH_GAUSSIAN_C, _cv.THRESH_BINARY, 41, 10)
                    # morphological opening to remove small noise
                    kernel = _cv.getStructuringElement(_cv.MORPH_RECT, (1,1))
                    morph = _cv.morphologyEx(th, _cv.MORPH_OPEN, kernel)
                    proc = morph
                except Exception:
                    proc = arr

                proc_img = Image.fromarray(proc)
                proc_img = ImageOps.autocontrast(proc_img)
                return proc_img

            # PIL fallback preprocessing
            proc = ImageOps.autocontrast(gray)
            proc = proc.filter(ImageFilter.MedianFilter(size=3))
            # simple binarize
            proc = proc.point(lambda p: 255 if p > 180 else 0).convert('L')
            proc = ImageOps.autocontrast(proc)
            return proc.convert('RGB')
        except Exception:
            logger.exception('Preprocessing failed; returning original image')
            return image
    
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
            for page in result.pages:
                for block in page.blocks:
                    for line in block.lines:
                        line_text = " ".join([getattr(word, 'value', '') for word in line.words])
                        if line_text.strip():
                            text_lines.append(line_text)
            full_text = "\n".join(text_lines)
            return full_text
        except Exception as e:
            logger.error(f"Text extraction error: {e}", exc_info=True)
            try:
                return result.export()
            except Exception:
                return ""

    def _extract_structured_from_result(self, result) -> Dict[str, Any]:
        """
        Extract structured output (text + bounding boxes) from docTR result
        """
        try:
            pages_out: List[Dict[str, Any]] = []
            for page in result.pages:
                page_text_lines: List[str] = []
                blocks_out: List[Dict[str, Any]] = []
                for block in page.blocks:
                    block_text = []
                    bbox = None
                    for line in block.lines:
                        line_text = " ".join([getattr(word, 'value', '') for word in line.words])
                        if line_text.strip():
                            block_text.append(line_text)
                    # try to get block bbox if available
                    try:
                        if hasattr(block, 'geometry') and block.geometry is not None:
                            geom = block.geometry
                            # some geometry objects provide to_xyxy()
                            if hasattr(geom, 'to_xyxy'):
                                bbox = list(geom.to_xyxy())
                            else:
                                # attempt common attrs
                                bbox = [getattr(geom, 'x1', 0), getattr(geom, 'y1', 0), getattr(geom, 'x2', 0), getattr(geom, 'y2', 0)]
                    except Exception:
                        bbox = None

                    blocks_out.append({'text': "\n".join(block_text), 'bbox': bbox})
                    page_text_lines.extend(block_text)

                pages_out.append({'text': "\n".join(page_text_lines), 'blocks': blocks_out})

            # If single-page result, return single structured dict, otherwise list
            if len(pages_out) == 1:
                return pages_out[0]
            return pages_out
        except Exception:
            logger.exception('Structured extraction failed')
            # Fallback to plain text export
            try:
                plain = result.export()
                return {'text': plain, 'blocks': []}
            except Exception:
                return {'text': '', 'blocks': []}