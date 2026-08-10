from typing import List, Dict, Any, Optional
from services.document_parser.models import ParsedDocumentWrapper, BlockItem

class LayoutAwareDocumentChunker:
    def chunk_document(self, parsed_doc: ParsedDocumentWrapper) -> List[Dict[str, Any]]:
        """
        Groups blocks into layout-aware semantic chunks and generates RAG metadata.
        """
        chunks = []
        document_id = None
        chunk_idx = 0
        
        for page in parsed_doc.document.pages:
            page_number = page.page_number
            flat_blocks = self._flatten_blocks(page.items)
            
            current_group: List[BlockItem] = []
            current_section = "Introduction"
            current_heading = ""
            
            for block in flat_blocks:
                if not document_id and block.document_id:
                    document_id = block.document_id
                
                # Check for headings to split chunks
                if block.type == "heading":
                    if current_group:
                        chunks.append(self._create_chunk(current_group, document_id, page_number, current_section, current_heading, chunk_idx))
                        chunk_idx += 1
                        current_group = []
                    
                    current_heading = block.text
                    current_section = block.text
                    current_group.append(block)
                    continue
                
                # Check for tables or images that should not be split
                if block.type in ("table", "image"):
                    if current_group and not all(b.type == "heading" for b in current_group):
                        chunks.append(self._create_chunk(current_group, document_id, page_number, current_section, current_heading, chunk_idx))
                        chunk_idx += 1
                        current_group = []
                        
                    current_group.append(block)
                    continue
                    
                # If we encounter content but current group holds a table/image, flush it (except captions)
                if current_group and any(b.type in ("table", "image") for b in current_group):
                    if block.type == "caption":
                        current_group.append(block)
                        continue
                    else:
                        chunks.append(self._create_chunk(current_group, document_id, page_number, current_section, current_heading, chunk_idx))
                        chunk_idx += 1
                        current_group = []
                
                current_group.append(block)
                
            if current_group:
                chunks.append(self._create_chunk(current_group, document_id, page_number, current_section, current_heading, chunk_idx))
                chunk_idx += 1
                
        return chunks

    def _flatten_blocks(self, items: List[BlockItem]) -> List[BlockItem]:
        flat = []
        sorted_items = sorted(items, key=lambda x: x.reading_order)
        for item in sorted_items:
            flat.append(item)
            if item.children:
                flat.extend(self._flatten_blocks(item.children))
        return sorted(flat, key=lambda x: x.reading_order)

    def _create_chunk(self, blocks: List[BlockItem], document_id: Optional[str], page_number: int, section: str, heading: str, chunk_index: int) -> Dict[str, Any]:
        content_lines = []
        block_ids = []
        bboxes = []
        reading_orders = []
        source_parser = "docling"
        
        for b in blocks:
            content_lines.append(b.text)
            block_ids.append(b.block_id)
            if b.bbox:
                bboxes.append(b.bbox)
            reading_orders.append(b.reading_order)
            source_parser = b.source_parser
            
        content = "\n\n".join(content_lines)
        primary_reading_order = min(reading_orders) if reading_orders else 0
        
        enclosing_bbox = None
        if bboxes:
            min_l = min(box[0] for box in bboxes)
            min_t = min(box[1] for box in bboxes)
            max_r = max(box[2] for box in bboxes)
            max_b = max(box[3] for box in bboxes)
            enclosing_bbox = [min_l, min_t, max_r, max_b]
            
        rag_header = (
            f"Document ID: {document_id}\n"
            f"Page Number: {page_number}\n"
            f"Section: {section}\n"
            f"Heading: {heading}\n"
            f"Block IDs: {', '.join(block_ids)}\n"
            f"BBox: {enclosing_bbox}\n"
            f"Chunk Index: {chunk_index}\n"
            f"Reading Order: {primary_reading_order}\n"
            f"Source Parser: {source_parser}\n"
            f"---\n"
        )
        
        full_content = rag_header + content
        
        return {
            "document_id": document_id,
            "page_number": page_number,
            "section": section,
            "heading": heading,
            "block_ids": block_ids,
            "bbox": enclosing_bbox,
            "chunk_index": chunk_index,
            "reading_order": primary_reading_order,
            "source_parser": source_parser,
            "content": full_content
        }
