import os
import uuid
import logging
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sqlalchemy as sa
import fitz # PyMuPDF

from database.database import SessionLocal
from models.models import Document, Page, DocumentResult, ActivityEvent, Chunk
from services.ocr_service import extract_text_from_image

logger = logging.getLogger("ocr_pipeline")

def parse_docx_text(file_path: str) -> str:
    """Natively extract text paragraphs from a DOCX file using zip structure."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"DOCX file not found: {file_path}")
    try:
        with zipfile.ZipFile(file_path) as docx:
            xml_content = docx.read('word/document.xml')
            root = ET.fromstring(xml_content)
            paragraphs = []
            for para in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                texts = [node.text for node in para.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if node.text]
                if texts:
                    paragraphs.append("".join(texts))
            return "\n".join(paragraphs)
    except Exception as e:
        logger.error(f"Error parsing DOCX file {file_path}: {str(e)}")
        raise e

def parse_txt_text(file_path: str) -> str:
    """Natively read text file content."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Text file not found: {file_path}")
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("Failed to decode text file with standard encodings.")

async def process_document_pipeline(document_id: uuid.UUID, file_path: str):
    logger.info(f"Starting background processing for document: {document_id}")
    
    # Create isolated database session
    async with SessionLocal() as db:
        # 1. Fetch document metadata
        stmt = select(Document).where(Document.id == document_id)
        res = await db.execute(stmt)
        document = res.scalar_one_or_none()
        
        if not document:
            logger.error(f"Document {document_id} not found in database. Aborting pipeline.")
            return

        upload_dir = os.path.dirname(file_path)
        file_basename = os.path.basename(file_path)
        file_id = file_basename.split('.')[0]
        ext = file_basename.split('.')[-1].lower()

        pages_data = []

        try:
            # 2. Extract content based on file type
            parsed_doc = None
            if ext == "pdf":
                from core.config import settings
                from services.document_parser.docling_parser import DoclingParser
                from services.document_parser.pymupdf_parser import PyMuPDFParser
                
                use_docling = getattr(settings, "USE_DOCLING", True)
                logger.info(f"Processing PDF document: {document.file_name}. USE_DOCLING={use_docling}")
                
                parser = DoclingParser() if use_docling else PyMuPDFParser()
                try:
                    parsed_doc = parser.parse(file_path, str(document_id))
                except Exception as parse_err:
                    logger.error(f"Selected parser failed: {str(parse_err)}. Falling back to PyMuPDF...")
                    parser = PyMuPDFParser()
                    parsed_doc = parser.parse(file_path, str(document_id))
                
                # Map parsed_doc to pages_data
                for page in parsed_doc.document.pages:
                    # Get text content by joining block texts
                    page_text = "\n\n".join([item.text for item in page.items if item.text])
                    # Try to find preview image in metadata/image_path
                    img_path = ""
                    for item in page.items:
                        if item.metadata and "image_path" in item.metadata:
                            img_path = item.metadata["image_path"]
                            break
                        if item.image_path:
                            img_path = item.image_path
                            break
                    
                    pages_data.append({
                        "page_number": page.page_number,
                        "text": page_text,
                        "image_path": img_path
                    })
                
            elif ext in ("jpg", "jpeg", "png"):
                # Image processing directly via PaddleOCR
                logger.info(f"Processing image document: {document.file_name}")
                text = extract_text_from_image(file_path)
                pages_data.append({
                    "page_number": 1,
                    "text": text,
                    "image_path": f"/files/{file_basename}"
                })
                
            elif ext == "docx":
                # DOCX processing
                logger.info(f"Processing DOCX document: {document.file_name}")
                text = parse_docx_text(file_path)
                pages_data.append({
                    "page_number": 1,
                    "text": text,
                    "image_path": ""
                })
                
            elif ext in ("txt", "csv"):
                # Text processing
                logger.info(f"Processing TXT document: {document.file_name}")
                text = parse_txt_text(file_path)
                pages_data.append({
                    "page_number": 1,
                    "text": text,
                    "image_path": ""
                })
                
            else:
                raise ValueError(f"Unsupported file extension: {ext}")

            # 3. Save page records
            page_objects = []
            for pdata in pages_data:
                page = Page(
                    document_id=document_id,
                    page_number=pdata["page_number"],
                    image_path=pdata["image_path"],
                    raw_text=pdata["text"]
                )
                db.add(page)
                page_objects.append(page)
            
            # Flush pages to populate their database UUIDs
            await db.flush()

            # 3.5 Run Layout-Aware Chunking Engine
            if ext == "pdf" and parsed_doc:
                from services.document_parser.chunking import LayoutAwareDocumentChunker
                chunker = LayoutAwareDocumentChunker()
                chunks = chunker.chunk_document(parsed_doc)
                
                chunk_objects = []
                for chk in chunks:
                    target_page = next((p for p in page_objects if p.page_number == chk["page_number"]), None)
                    if not target_page:
                        target_page = page_objects[0] if page_objects else None
                        
                    if target_page:
                        chunk_obj = Chunk(
                            page_id=target_page.id,
                            chunk_index=chk["chunk_index"],
                            content=chk["content"]
                        )
                        db.add(chunk_obj)
                        chunk_objects.append(chunk_obj)
            else:
                # Legacy chunking fallback
                from services.chunking_service import ChunkingContext, LayoutAwareChunkingStrategy
                chunking_ctx = ChunkingContext(LayoutAwareChunkingStrategy())

                chunk_objects = []
                for page in page_objects:
                    chunks = chunking_ctx.chunk_page(
                        text=page.raw_text or "",
                        document_name=document.file_name,
                        page_number=page.page_number,
                        target_tokens=500,
                        max_tokens=800,
                        overlap_tokens=100
                    )
                    for idx, chunk_content in enumerate(chunks):
                        chunk_obj = Chunk(
                            page_id=page.id,
                            chunk_index=idx,
                            content=chunk_content
                        )
                        db.add(chunk_obj)
                        chunk_objects.append(chunk_obj)
            
            # Flush chunks to populate their database UUIDs
            await db.flush()

            # 3.7 Generate chunk embeddings using active model
            from services.embedding_service import ingest_chunk_embeddings
            active_model = os.getenv("ACTIVE_EMBEDDING_MODEL", "nomic-embed-text")
            chunk_ids = [c.id for c in chunk_objects]
            if chunk_ids:
                logger.info(f"Generating embeddings for {len(chunk_ids)} chunks using model: {active_model}")
                await ingest_chunk_embeddings(db, chunk_ids, active_model)

            # 4. Save aggregate result (Upsert to prevent duplicate unique key constraint failures)
            full_text = "\n".join([p["text"] for p in pages_data])
            stmt = select(DocumentResult).where(DocumentResult.document_id == document_id)
            res = await db.execute(stmt)
            existing_result = res.scalar_one_or_none()

            structured_json = parsed_doc.model_dump() if parsed_doc else None

            if existing_result:
                existing_result.full_text = full_text
                if structured_json:
                    existing_result.structured_data = structured_json
            else:
                result = DocumentResult(
                    document_id=document_id,
                    full_text=full_text,
                    structured_data=structured_json
                )
                db.add(result)

            # 5. Log activity event
            event = ActivityEvent(
                user_id=document.user_id,
                project_id=document.project_id,
                action_name="DOCUMENT_PROCESSED",
                payload={"document_id": str(document_id), "pages_count": len(pages_data)}
            )
            db.add(event)

            await db.commit()
            logger.info(f"Document {document_id} pipeline completed successfully.")


        except Exception as e:
            await db.rollback()
            logger.error(f"Error executing OCR pipeline for document {document_id}: {str(e)}")
            # Log failure event
            try:
                failure_event = ActivityEvent(
                    user_id=document.user_id,
                    project_id=document.project_id,
                    action_name="DOCUMENT_PROCESSING_FAILED",
                    payload={"document_id": str(document_id), "error": str(e)}
                )
                db.add(failure_event)
                await db.commit()
            except Exception as fail_err:
                logger.error(f"Could not persist failure event log: {str(fail_err)}")
