from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ExtractedPageSchema(BaseModel):
    pageNumber: int
    text: str
    imageUrl: str

class PatientInfoSchema(BaseModel):
    name: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    date: Optional[str] = None

class MedicineSchema(BaseModel):
    name: str
    dosage: str
    frequency: str
    duration: str

class MedicalTestResultSchema(BaseModel):
    parameter: str
    result: str
    unit: str
    range: str

class StructuredMedicalDataSchema(BaseModel):
    patientInfo: PatientInfoSchema
    testResults: List[MedicalTestResultSchema]
    medicines: List[MedicineSchema]
    diagnosis: Optional[str] = ""
    advice: Optional[str] = ""
    summary: Optional[str] = ""

class DocumentUploadResponseSchema(BaseModel):
    fileType: str
    fileName: str
    fileUrl: str
    totalPages: int
    pages: List[ExtractedPageSchema]
    structuredData: Optional[StructuredMedicalDataSchema] = None
    fullText: str
