# DocExtract - Comprehensive Project Documentation

DocExtract is an AI-powered document text extraction system. It consists of a high-performance **React + TypeScript frontend** and a **FastAPI Python backend** with hardware-accelerated optical character recognition (OCR) and layout rendering.

---

## 🎨 Frontend Architecture

The frontend is a single-page application (SPA) focused on clean user experience, real-time feedback, and high-resolution document inspection.

### 🛠️ Core Technologies
* **Framework**: [React 18](https://react.dev/) with [TypeScript](https://www.typescriptlang.org/).
* **Bundler & Tooling**: [Vite](https://vitejs.dev/) with SWC (Speedy Web Compiler) for instant Hot Module Replacement (HMR).
* **Styling**: [TailwindCSS](https://tailwindcss.com/) for layout constraints and utilities.
* **Animations**: [Framer Motion](https://www.framer.com/motion/) for dropzone and panel transitions.
* **Icons**: [Lucide React](https://lucide.dev/).

### 📂 Key Components & Layout
* **`src/pages/Index.tsx`**: Main controller holding state for file selection, extraction progress, active page index, and errors.
* **`src/components/FileDropzone.tsx`**: Drag-and-drop file uploader that restricts files to PDFs and images, creates previewable URLs, and handles loading animations.
* **`src/components/DocumentViewer.tsx`**: Renders PDF/image preview files side-by-side using the backend-generated preview PNG files.
* **`src/components/TextPanel.tsx`**: Displays clean, extracted raw text side-by-side with document previews. Offers inline word-highlight search and a copy utility.

### ⚙️ Specialized Frontend Implementations
* **Self-Healing Port Cleaner (`src/main.tsx`)**: Auto-unregisters stale Progressive Web App (PWA) service workers from other projects on port `5173` to prevent blank screen load failures.
* **Wide-Screen Layout**: Configured with a `max-width` limit of **`115rem` (1840px)** to support clean dual-pane inspection on large desktop monitors.

---

## ⚙️ Backend Architecture

The backend is a fast Python API service designed to run on the local CPU, optimizing extraction tasks and caching neural networks to ensure minimal latency.

### 🛠️ Core Technologies
* **API Framework**: [FastAPI](https://fastapi.tiangolo.com/) for asynchronous REST endpoint handling.
* **Web Server**: [Uvicorn](https://www.uvicorn.org/) for high-throughput local hosting.
* **Libraries**:
  * **PyMuPDF (`fitz`)**: Lightning-fast parsing of native digital PDFs and page-to-image rasterization.
  * **PaddlePaddle (v3.2.2) & PaddleOCR**: Highly accurate deep learning-based OCR framework.

### 📂 Key Backend Modules (`backendPY/services/`)
* **`pdf_extractor.py`**: Coordinates multi-page document parsing:
  1. Extracts native text (if digital/selectable) page-by-page.
  2. Generates a high-resolution PNG preview of each page and saves it locally.
  3. Falls back to OCR on individual page images if no native text is found.
* **`ocr_service.py`**: A thread-safe singleton wrapper around the PaddleOCR model to ensure the network is only loaded once in memory.
* **`medical_parser.py`**: Local heuristics parser mapping text patterns (demographics, test results) to structured payloads.

---

## ⚡ Performance Optimizations

To run deep-learning OCR locally on CPU without hanging, the following configurations were applied:

1. **Intel oneDNN/MKLDNN Vectorization**: Locked **`paddlepaddle==3.2.2`** in dependencies. This resolves a PIR executor crash present in newer releases, allowing us to enable `enable_mkldnn=True` to vectorize matrix operations on the CPU, achieving a **5x speedup**.
2. **Preprocessor Bypassing in Constructor**: 
   ```python
   PaddleOCR(
       use_doc_orientation_classify=False,
       use_doc_unwarping=False,
       use_textline_orientation=False
   )
   ```
   By disabling orientation classifiers directly in the class constructor, we prevent PaddleOCR from loading 3 unused neural networks, cutting model load time from **13.2 seconds** down to **1.5 seconds**.
3. **Ignored Hot-Reload Folders**: Added `watch.ignored: ["**/public/**"]` inside `vite.config.ts` to prevent the Vite file watcher from crash-looping when PDF page previews or temporary files are created on Windows.

---

## 📦 Full Dependency Manifest

### Backend (`requirements.txt`)
* `fastapi==0.109.0`
* `uvicorn==0.27.0`
* `python-multipart==0.0.6`
* `pymupdf==1.23.8` (PyMuPDF)
* `paddlepaddle==3.2.2` (Locked CPU runtime)
* `paddleocr>=2.7.0` (OCR service)
* `Pillow==10.2.0` (Image processing)
* `opencv-python-headless==4.9.0.80` (Computer vision utility)
* `numpy<2`

### Frontend (`package.json`)
* `react` & `react-dom` (v18.3.1)
* `framer-motion` (v12.26.2)
* `lucide-react` (v0.462.0)
* `tailwindcss` (v3.4.17)
* `typescript` (v5.8.3)
* `vite` (v5.4.19)
