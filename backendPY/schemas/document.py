from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

import uuid

class SaveDocumentRequest(BaseModel):
    file_name: str
    file_type: str
    file_path: str
    full_text: str
    structured_data: Optional[Any] = None
    project_id: Optional[uuid.UUID] = None

class DocumentResultResponse(BaseModel):
    id: str
    full_text: str
    structured_data: Optional[Any] = None

class DocumentResponse(BaseModel):
    id: str
    user_id: str
    file_name: str
    file_type: str
    file_path: str
    created_at: datetime
    status: str = "uploaded"
    result: Optional[DocumentResultResponse] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    skip: int
    limit: int

class BulkDeleteDocumentsRequest(BaseModel):
    document_ids: List[uuid.UUID]
