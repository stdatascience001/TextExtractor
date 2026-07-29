# Medical Report OCR & PDF Text Extraction API

A robust FastAPI-based backend service designed to extract text from PDF documents and images (JPG/PNG), specifically tailored for parsing and structuring medical report data.

## Features

- **Document Processing**: Extract text from both PDF documents and images (JPG, JPEG, PNG).
- **Medical Report Parsing**: Automatically processes extracted text to find structured medical data points.
- **Image OCR**: Utilizes Tesseract OCR and OpenCV for high-accuracy text extraction from images.
- **Fast & Async**: Built on FastAPI for high performance and asynchronous request handling.
- **File Validation**: Built-in size limits (10MB max) and file extension validation.
- **Static File Serving**: Serves processed documents and images securely via a mounted static route.

## Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Server**: [Uvicorn](https://www.uvicorn.org/)
- **PDF Extraction**: [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/)
- **Image OCR**: [Tesseract (pytesseract)](https://github.com/madmaze/pytesseract), [OpenCV](https://opencv.org/)
- **Image Processing**: [Pillow](https://python-pillow.org/)

## Prerequisites

Before running this project, ensure you have the following installed on your system:
- **Python 3.8+**
- **Tesseract OCR**: You must have Tesseract installed on your system and added to your system's PATH.
  - *Windows*: Download the installer from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki).
  - *Linux*: `sudo apt-get install tesseract-ocr`
  - *Mac*: `brew install tesseract`

## Installation & Setup

1. **Clone or navigate to the project directory**:
   ```bash
   cd backendPY
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - **Windows**:
     ```powershell
     .\venv\Scripts\Activate
     ```
   - **Mac/Linux**:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Server

Start the application with live-reloading enabled:

```bash
python -m uvicorn main:app --reload
```

The server will start on `http://127.0.0.1:8000`. 
You can view the auto-generated Swagger UI documentation at `http://127.0.0.1:8000/docs`.

## API Endpoints

### 1. Health Check
- **Endpoint**: `GET /`
- **Description**: Verifies that the API is up and running.
- **Response**:
  ```json
  {
    "status": "ok",
    "message": "PDF Reader API is running"
  }
  ```

### 2. Upload Document
- **Endpoint**: `POST /upload`
- **Content-Type**: `multipart/form-data`
- **Parameters**: 
  - `file`: The document or image file to process (max 10MB, allowed types: pdf, jpg, jpeg, png).
- **Description**: Uploads a file, extracts the text using PyMuPDF or Tesseract OCR, and parses medical report structures.
- **Response**:
  ```json
  {
    "fileType": "pdf | image",
    "fileName": "example.pdf",
    "fileUrl": "/files/uuid.pdf",
    "totalPages": 3,
    "pages": [
      {
        "pageNumber": 1,
        "text": "Extracted text...",
        "imageUrl": "/files/uuid.pdf" 
      }
    ],
    "structuredData": { ... },
    "fullText": "Full extracted text string"
  }
  ```

## Project Structure

```
backendPY/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── services/
│   ├── pdf_extractor.py    # PyMuPDF extraction logic
│   ├── image_extractor.py  # Tesseract OCR & OpenCV logic
│   └── medical_parser.py   # NLP/Regex logic for structuring medical data
└── uploads/                # Directory for temporarily storing uploaded files
```