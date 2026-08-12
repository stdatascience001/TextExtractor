from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class CellInfo(BaseModel):
    coordinate: str  # e.g., "A1"
    value: str
    formula: Optional[str] = None
    is_merged: bool = False
    merged_range: Optional[str] = None

class RowInfo(BaseModel):
    row_index: int  # 1-indexed row number
    cells: Dict[str, str]  # coordinate -> cell value string
    raw_values: List[str]

class SheetInfo(BaseModel):
    sheet_name: str
    headers: List[str]
    rows: List[RowInfo]
    row_count: int
    col_count: int
