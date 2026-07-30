from fastapi import UploadFile
from core.config import settings
from core.exceptions import APIException

def validate_file(upload: UploadFile) -> str:
    filename = upload.filename or ""
    if "." not in filename:
        raise APIException(
            status_code=422,
            detail="File has no extension"
        )
        
    ext = filename.split(".")[-1].lower()

    if ext not in settings.allowed_extensions_set:
        raise APIException(
            status_code=422,
            detail="Unsupported file format"
        )

    return ext
