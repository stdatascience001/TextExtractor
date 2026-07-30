import os
import uuid
from fastapi import APIRouter, UploadFile, File
from core.config import settings
from core.exceptions import APIException
from core.logging import logger
from utils.validation import validate_file

from services.pdf_extractor import extract_pdf_text
from services.ocr_service import extract_text_from_image
from services.medical_parser import parse_medical_report
from schemas.upload import DocumentUploadResponseSchema

router = APIRouter()

@router.post("/upload", response_model=DocumentUploadResponseSchema)
async def upload_file(file: UploadFile = File(...)):
    logger.info(f"--- Received upload: {file.filename} ---")
    ext = validate_file(file)

    contents = await file.read()
    if len(contents) > settings.MAX_FILE_SIZE:
        raise APIException(
            status_code=422,
            detail=f"File size exceeds {settings.MAX_FILE_SIZE // (1024 * 1024)}MB limit"
        )

    file_id = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, file_id)

    with open(file_path, "wb") as f:
        f.write(contents)

    try:
        if ext == "pdf":
            pages = extract_pdf_text(file_path)
            file_type = "pdf"
        else:
            text = extract_text_from_image(file_path)
            pages = [{
                "pageNumber": 1, 
                "text": text,
                "imageUrl": f"/files/{file_id}"
            }]
            file_type = "image"

        full_text = "\n".join([p["text"] for p in pages])
        logger.debug(f"Full text extracted (first 200 chars):\n{full_text[:200]}...")
        structured_data = parse_medical_report(full_text)

    except Exception as e:
        logger.exception(f"Error processing file {file.filename}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise APIException(
            status_code=500,
            detail=str(e)
        )

    return {
        "fileType": file_type,
        "fileName": file.filename,
        "fileUrl": f"/files/{file_id}",
        "totalPages": len(pages),
        "pages": pages,
        "structuredData": structured_data,
        "fullText": full_text
    }
