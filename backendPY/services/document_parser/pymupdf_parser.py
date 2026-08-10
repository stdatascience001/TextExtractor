import fitz
import os
import uuid
from datetime import datetime
from services.document_parser.base_parser import BaseDocumentParser
from services.document_parser.models import ParsedDocumentWrapper, DocumentModel, PageInfo, BlockItem
from services.ocr_service import extract_text_from_image
from core.config import settings
from core.logging import logger

class PyMuPDFParser(BaseDocumentParser):
    def parse(self, file_path: str, document_id: str) -> ParsedDocumentWrapper:
        logger.info(f"[PyMuPDFParser] Initiating parsing for: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        doc = fitz.open(file_path)
        upload_dir = os.path.dirname(file_path)
        file_basename = os.path.basename(file_path)
        file_id = file_basename.split('.')[0]
        
        pages_list = []
        for i, page in enumerate(doc, start=1):
            text = page.get_text().strip()
            
            # Generate preview image path
            image_name = f"{file_id}_page_{i}.png"
            image_path_full = os.path.join(upload_dir, image_name)
            
            # Render page as image for preview
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            pix.save(image_path_full)
            
            # Fallback to OCR if no native text
            if not text:
                logger.info(f"[PyMuPDFParser] Page {i} lacks native text. Running OCR fallback...")
                try:
                    text = extract_text_from_image(image_path_full)
                except Exception as ocr_err:
                    logger.error(f"[PyMuPDFParser] OCR fallback failed: {str(ocr_err)}")
                    text = ""
            
            block = BlockItem(
                id=str(uuid.uuid4()),
                block_id=str(uuid.uuid4()),
                document_id=document_id,
                page_number=i,
                parent_block_id=None,
                type="paragraph",
                text=text,
                bbox=[0.0, 0.0, float(page.rect.width), float(page.rect.height)],
                reading_order=1,
                heading_level=None,
                confidence=1.0,
                source_parser="pymupdf",
                created_at=datetime.utcnow().isoformat(),
                metadata={"image_path": f"/files/{image_name}"},
                children=[]
            )
            
            pages_list.append(PageInfo(
                page_number=i,
                width=float(page.rect.width),
                height=float(page.rect.height),
                items=[block]
            ))
            
        logger.info(f"[PyMuPDFParser] Successfully completed parsing. Extracted {len(pages_list)} pages.")
        return ParsedDocumentWrapper(
            document=DocumentModel(
                metadata={"source_parser": "pymupdf"},
                pages=pages_list
            )
        )
