from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class BlockItem(BaseModel):
    id: str
    block_id: str
    document_id: Optional[str] = None
    page_number: int
    parent_block_id: Optional[str] = None
    type: str  # heading, paragraph, bullet_list, numbered_list, table, image, caption, header, footer, code, quote, formula, footnote, sheet_header, table_row
    text: str
    bbox: Optional[List[float]] = None
    reading_order: int
    heading_level: Optional[int] = None
    confidence: float = 1.0
    source_parser: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)
    image_path: Optional[str] = None
    table_html: Optional[str] = None
    children: List["BlockItem"] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True
    }

# Enable recursive model reference resolution
BlockItem.model_rebuild()

class PageInfo(BaseModel):
    page_number: int
    width: float
    height: float
    items: List[BlockItem] = Field(default_factory=list)
    image_path: Optional[str] = None

class DocumentModel(BaseModel):
    metadata: Dict[str, Any] = Field(default_factory=dict)
    pages: List[PageInfo] = Field(default_factory=list)

class ParsedDocumentWrapper(BaseModel):
    document: DocumentModel
