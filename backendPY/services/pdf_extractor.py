import os
import fitz  # PyMuPDF
from services.ocr_service import extract_text_from_image


def extract_pdf_text(path: str):
    doc = fitz.open(path)
    results = []
    
    # Get the directory of the uploaded file to store page images
    upload_dir = os.path.dirname(path)
    file_id = os.path.basename(path).split('.')[0]

    print(f"Processing PDF: {path} ({len(doc)} pages)")
    for i, page in enumerate(doc, start=1):
        print(f"  - Extracting page {i}...")
        # 1. Extract text if possible
        text = page.get_text().strip()

        # 2. Generate preview image for this page
        print(f"  - Generating preview for page {i}...")
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Better resolution
        image_name = f"{file_id}_page_{i}.png"
        image_path = os.path.join(upload_dir, image_name)
        pix.save(image_path)

        # 3. If no text extracted, try OCR on the generated image
        if not text:
            print(f"  - [OCR] No native text on page {i}, running OCR...")
            text = extract_text_from_image(image_path)

        results.append({
            "pageNumber": i,
            "text": text,
            "imageUrl": f"/files/{image_name}"
        })
    print(f"Done processing PDF: {path}")

    return results

