import os
import uuid
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from services.document_parser.base_parser import BaseDocumentParser
from services.document_parser.models import ParsedDocumentWrapper, DocumentModel, PageInfo, BlockItem
from core.config import settings
from core.logging import logger

# Lazy initialization helper for Docling DocumentConverter
_converter_instance = None

def get_docling_converter() -> DocumentConverter:
    global _converter_instance
    if _converter_instance is None:
        logger.info("Initializing Docling DocumentConverter...")
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.generate_picture_images = True
        
        _converter_instance = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
    return _converter_instance

class DoclingParser(BaseDocumentParser):
    def get_image_storage_path(self, document_id: str) -> tuple[str, str]:
        base_dir = os.path.join(settings.UPLOAD_DIR, "documents")
        fs_path = os.path.join(base_dir, document_id, "images")
        
        try:
            rel = os.path.relpath(fs_path, settings.UPLOAD_DIR)
            url_path = f"/files/{rel.replace(os.sep, '/')}"
        except Exception:
            url_path = f"/files/documents/{document_id}/images"
            
        return fs_path, url_path

    def _determine_list_type(self, text: str) -> str:
        cleaned = text.strip()
        if re.match(r'^(?:\(?\d+[.)]?|(?:\(?|[a-zA-Z])[.)]?|(?:\(?|[ivxIVX]+)[.)]?)\s+', cleaned):
            return "numbered_list"
        return "bullet_list"

    def parse(self, file_path: str, document_id: str) -> ParsedDocumentWrapper:
        logger.info(f"[DoclingParser] Parsing document: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Configurable image directories
        image_fs_dir, image_url_dir = self.get_image_storage_path(document_id)
        os.makedirs(image_fs_dir, exist_ok=True)

        # Execute conversion using Docling
        converter = get_docling_converter()
        conversion_result = converter.convert(file_path)
        doc = conversion_result.document

        # 1. Fetch Page dimensions mapping
        pages_meta = {}
        if hasattr(doc, "pages"):
            if isinstance(doc.pages, dict):
                for p_num_str, p_info in doc.pages.items():
                    try:
                        p_num = int(p_num_str)
                        width = float(p_info.size.width) if hasattr(p_info, "size") and p_info.size else 612.0
                        height = float(p_info.size.height) if hasattr(p_info, "size") and p_info.size else 792.0
                        pages_meta[p_num] = {"width": width, "height": height}
                    except Exception:
                        pass
            elif isinstance(doc.pages, list):
                for idx, p_info in enumerate(doc.pages, start=1):
                    try:
                        width = float(p_info.size.width) if hasattr(p_info, "size") and p_info.size else 612.0
                        height = float(p_info.size.height) if hasattr(p_info, "size") and p_info.size else 792.0
                        pages_meta[idx] = {"width": width, "height": height}
                    except Exception:
                        pass

        # 2. Iterate elements and build flat lists + structural mapping
        reading_order_counter = 1
        all_blocks: List[BlockItem] = []
        stack: List[Dict[str, Any]] = []

        for item, level in doc.iterate_items():
            cls_name = item.__class__.__name__
            
            # Base variables
            block_uuid = str(uuid.uuid4())
            block_type = "paragraph"
            block_text = ""
            heading_level = None
            table_html = None
            image_path = None
            metadata = {}
            confidence = 1.0

            # Provenance layout mapping
            page_no = 1
            bbox = None
            if hasattr(item, "prov") and item.prov:
                prov = item.prov[0]
                if hasattr(prov, "page_no") and prov.page_no:
                    page_no = int(prov.page_no)
                if hasattr(prov, "bbox") and prov.bbox:
                    b = prov.bbox
                    if hasattr(b, "l"):
                        bbox = [float(b.l), float(b.t), float(b.r), float(b.b)]
                    elif hasattr(b, "as_tuple"):
                        bbox = list(b.as_tuple())

            # Text content
            if hasattr(item, "text"):
                block_text = item.text or ""

            # Class mapping
            if "Table" in cls_name:
                block_type = "table"
                try:
                    table_html = item.export_to_html(doc=doc)
                except Exception:
                    table_html = ""
                try:
                    markdown = item.export_to_markdown(doc=doc)
                except Exception:
                    markdown = ""
                try:
                    df = item.export_to_dataframe(doc=doc)
                    rows_count = len(df.index) if df is not None else 0
                    cols_count = len(df.columns) if df is not None else 0
                except Exception:
                    rows_count, cols_count = 0, 0
                
                metadata = {
                    "html": table_html,
                    "markdown": markdown,
                    "rows": rows_count,
                    "columns": cols_count
                }
            elif "Picture" in cls_name:
                block_type = "image"
                pil_img = None
                try:
                    if hasattr(item, "get_image"):
                        pil_img = item.get_image(doc)
                    elif hasattr(item, "image") and item.image:
                        if hasattr(item.image, "pil_image") and item.image.pil_image:
                            pil_img = item.image.pil_image
                except Exception as img_err:
                    logger.error(f"[DoclingParser] Image extract failed: {str(img_err)}")

                if pil_img:
                    image_name = f"image_{reading_order_counter}.png"
                    fs_dest = os.path.join(image_fs_dir, image_name)
                    pil_img.save(fs_dest)
                    image_path = f"{image_url_dir}/{image_name}"
                    metadata = {
                        "image_path": image_path,
                        "width": pil_img.width,
                        "height": pil_img.height,
                        "bbox": bbox,
                        "page_number": page_no
                    }
            else:
                # Text label mappings
                lbl = getattr(item, "label", "").lower()
                if lbl in ("title", "section_header"):
                    block_type = "heading"
                    heading_level = level + 1
                elif lbl == "list_item":
                    block_type = self._determine_list_type(block_text)
                elif lbl == "page_header":
                    block_type = "header"
                elif lbl == "page_footer":
                    block_type = "footer"
                elif lbl == "caption":
                    block_type = "caption"
                elif lbl == "code":
                    block_type = "code"
                elif lbl == "footnote":
                    block_type = "footnote"
                elif lbl == "formula":
                    block_type = "formula"
                elif lbl in ("reference", "quote"):
                    block_type = "quote"
                else:
                    block_type = "paragraph"

            # Create BlockItem instance
            block_obj = BlockItem(
                id=block_uuid,
                block_id=block_uuid,
                document_id=document_id,
                page_number=page_no,
                parent_block_id=None,
                type=block_type,
                text=block_text,
                bbox=bbox,
                reading_order=reading_order_counter,
                heading_level=heading_level,
                confidence=confidence,
                source_parser="docling",
                created_at=datetime.utcnow().isoformat(),
                metadata=metadata,
                image_path=image_path,
                table_html=table_html,
                children=[]
            )
            
            # Parenting tree layout stack reconstruction
            while stack and stack[-1]["level"] >= level:
                stack.pop()

            if stack:
                parent = stack[-1]["block"]
                block_obj.parent_block_id = parent.block_id
                parent.children.append(block_obj)

            stack.append({"level": level, "block": block_obj})
            all_blocks.append(block_obj)
            reading_order_counter += 1

        # 3. Assemble document pages
        max_page = max(pages_meta.keys()) if pages_meta else 1
        if all_blocks:
            max_page = max(max_page, max(b.page_number for b in all_blocks))

        pages_list = []
        for p in range(1, max_page + 1):
            meta = pages_meta.get(p, {"width": 612.0, "height": 792.0})
            
            # Root items on this page: blocks of this page that either have no parent at all, 
            # or whose parent is on a different page.
            page_blocks = [
                b for b in all_blocks 
                if b.page_number == p and (
                    not b.parent_block_id or 
                    next((x for x in all_blocks if x.block_id == b.parent_block_id), None) is None or
                    next((x for x in all_blocks if x.block_id == b.parent_block_id), None).page_number != p
                )
            ]
            
            pages_list.append(PageInfo(
                page_number=p,
                width=meta["width"],
                height=meta["height"],
                items=page_blocks
            ))

        logger.info(f"[DoclingParser] Successfully converted document. Pages: {len(pages_list)}, Blocks: {len(all_blocks)}")
        return ParsedDocumentWrapper(
            document=DocumentModel(
                metadata={"source_parser": "docling"},
                pages=pages_list
            )
        )
