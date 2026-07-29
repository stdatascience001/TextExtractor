import os
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from services.pdf_extractor import extract_pdf_text
from services.ocr_service import extract_text_from_image
from services.medical_parser import parse_medical_report


UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")


def validate_file(upload: UploadFile) -> str:
    ext = upload.filename.split(".")[-1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail="Unsupported file format"
        )

    return ext


@app.get("/")
async def root():
    return {"status": "ok", "message": "PDF Reader API is running"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    print(f"--- Recieved upload: {file.filename} ---")
    ext = validate_file(file)

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=422,
            detail="File size exceeds 10MB limit"
        )

    file_id = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, file_id)

    with open(file_path, "wb") as f:
        f.write(contents)

    try:
        if ext == "pdf":
            pages = extract_pdf_text(file_path)
            file_type = "pdf"
        else:
            text = extract_text_from_image(file_path)
            # For direct images, we provide the file URL as the imageUrl for the single "page"
            pages = [{
                "pageNumber": 1, 
                "text": text,
                "imageUrl": f"/files/{file_id}"
            }]
            file_type = "image"

        # Aggregate all text for medical parsing
        full_text = "\n".join([p["text"] for p in pages])
        print(f"DEBUG: Full text extracted (first 200 chars):\n{full_text[:200]}...")
        structured_data = parse_medical_report(full_text)

    except Exception as e:
        import traceback
        traceback.print_exc()  # This will print the actual error to the terminal
        # Clean up the file if processing fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    return {
        "fileType": file_type,
        "fileName": file.filename,
        "fileUrl": f"/files/{file_id}",  # Original file
        "totalPages": len(pages),
        "pages": pages,
        "structuredData": structured_data,
        "fullText": full_text
    }


