# DocExtract: AI-Powered Document Text Extraction System

DocExtract is a production-quality, open-source document intelligence system that extracts, cleans, and presents text from PDFs, scanned documents, and images.

This repository contains both the **FastAPI Python backend** (with hardware-accelerated PaddleOCR) and the **React + TypeScript frontend** (using TailwindCSS and Framer Motion).

![DocExtract Demo](frontend/public/FinalGIF.gif)

---

## 🏗️ System Architecture

The application is structured into two main components:
1. **`backendPY/`**: FastAPI REST API coordinating document extraction.
   * **PyMuPDF (`fitz`)**: Parses digital PDFs instantly and renders pages into preview PNGs.
   * **PaddleOCR (v3.2.2)**: Performs high-accuracy optical character recognition (OCR) on scanned PDFs or raw images.
2. **`frontend/`**: Interactive user interface.
   * **React + Vite + TypeScript**: Hot-reloading, component-driven client-side application.
   * **Framer Motion**: Smooth micro-animations and visual transitions.
   * **Split View**: Left side displays the page-by-page document preview; right side shows the search-enabled raw text layout.

---

## 🚀 Installation & Local Setup

Follow these steps to set up and run both the backend and frontend services on your local machine.

### 📋 Prerequisites
* **Python**: v3.10 to v3.12 (Recommend v3.12)
* **Node.js**: v18.0 or higher
* **Package Managers**: `pip` and `npm`

---

### 🐍 1. Backend Setup (`backendPY`)

1. **Navigate to the backend directory**:
   ```bash
   cd D:\Paras0218\PdfReader\backendPY
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment** (Windows):
   ```bash
   .\venv\Scripts\activate
   ```

4. **Install backend dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: This locks `paddlepaddle==3.2.2` to ensure stability and compatibility with CPU hardware vectorization.*

5. **Start the FastAPI server**:
   ```bash
   python -m uvicorn main:app --reload
   ```
   * The backend will run on: **[http://localhost:8000](http://localhost:8000)**.
   * Swagger documentation will be available at: **[http://localhost:8000/docs](http://localhost:8000/docs)**.

---

### ⚛️ 2. Frontend Setup (`frontend`)

1. **Open a new terminal and navigate to the frontend directory**:
   ```bash
   cd D:\Paras0218\PdfReader\frontend
   ```

2. **Install frontend dependencies**:
   ```bash
   npm install
   ```

3. **Start the Vite development server**:
   ```bash
   npm run dev
   ```
   * The client application will launch at: **[http://localhost:5173](http://localhost:5173)**.

---

## ⚡ Performance Optimizations Implemented

* **oneDNN/MKLDNN Hardware Acceleration**: Configured `enable_mkldnn=True` in the PaddleOCR pipeline on CPU. This compiles matrix math operations to hardware vector instructions, yielding a **4x to 5x speed boost**.
* **Pre-empted Preprocessors**: Bypassed document layout classifiers, unwarp checking, and textline orientation directly inside the `PaddleOCR` class constructor. This reduces cold-start load time from **13.2 seconds** down to **1.5 seconds**.
* **Model versioning**: Uses lightweight `PP-OCRv4` mobile inference models, keeping memory usage minimal.
* **Auto-unregistration script**: Automatically clears stale PWA service workers on port `5173` to prevent blank white screens during project hot-swaps.

---

## 🗃️ Git Version Control Rules
* **Exclusions**: The `.gitignore` at the workspace root ensures that the virtual environment (`venv/`), static client-side build files (`dist/`), packages (`node_modules/`), and user uploaded documents under `backendPY/uploads/` are never committed to the remote repository.
* **Embed Repos**: Embedded `.git` files inside components are cleaned, ensuring the entire workspace commits natively as a single parent project.
