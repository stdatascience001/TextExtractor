# 📄 DocExtract: AI-Powered Document Intelligence

**DocExtract** is a production-ready, open-source document intelligence system. It seamlessly extracts, cleans, and presents text from PDFs, scanned documents, and raw images using a powerful AI-driven backend and a stunning, highly polished frontend interface.

![DocExtract Demo](frontend/public/FinalGIF.gif)

---

## 🌟 Key Features

* **Intelligent Text Extraction**: Upload PDFs or images and instantly extract text using hardware-accelerated Optical Character Recognition (OCR) and advanced document parsers.
* **Premium User Interface**: A beautifully crafted React frontend featuring:
  * 🧊 **Glassmorphism Design**: Sleek, semi-transparent UI elements with beautiful blur effects (Tooltips, Dropdowns, Popovers).
  * 🪄 **Micro-interactions**: Fluid, physics-based animations powered by Framer Motion.
  * 🌗 **Split-Pane Viewer**: High-resolution side-by-side document inspection and raw text extraction views.
  * 📁 **Collapsible Premium Sidebar**: Responsive stateful sidebar featuring tooltips for collapsed states.
* **Document Dashboard**: A robust management dashboard to view, filter, sort, and delete your extraction history.
* **Secure Authentication**: Full JWT-based authentication system with user profiles, allowing secure and private document storage.

---

## ⚙️ Document Processing & Embedding Flow

The system processes documents asynchronously from upload to vectorization using the following multi-stage pipeline:

```mermaid
graph TD
    A[User Uploads Document] --> B{Route by File Type}
    B -- PDF --> C[Docling / PyMuPDF Parser]
    B -- JPG/JPEG/PNG --> D[PaddleOCR Engine]
    B -- DOCX --> E[Native XML Paragraph Extractor]
    B -- TXT/CSV --> F[Plain Text Decoder]
    
    C --> G[Page & Layout Block Identification]
    D --> H[Optical Character Recognition]
    E --> I[Plain Text Output]
    F --> I
    
    G --> J[Layout-Aware Chunking Engine]
    H --> K[Fallback Sliding Window Chunker]
    I --> K
    
    J --> L[DB Persistence: Pages & Chunks]
    K --> L
    
    L --> M[Status: ready_for_embedding]
    
    subgraph Asynchronous Background Worker
        N[Embedding Worker Polls DB] --> O[Fetch Chunks]
        O --> P[Generate Embeddings via MockEmbeddingAdapter]
        P --> Q[Save Vectors to DB]
        Q --> R[Status: completed]
    end
    
    M -. Picked up by loop .-> N
```

### 1. Document Ingestion & Routing
When a document is uploaded, it is saved in the `uploads/` directory, and the system routes processing based on the file extension:
* **PDF**: Handled by **DoclingParser** (or falls back to **PyMuPDFParser**). It parses structural elements (paragraphs, tables, lists) alongside page boundaries.
* **Images (`.jpg`, `.jpeg`, `.png`)**: Handled by **PaddleOCR** (`extract_text_from_image`), which extracts text lines directly.
* **DOCX**: Handled natively by extracting XML paragraph tags from the docx zip archive.
* **TXT/CSV**: Handled by a multi-encoding plain text decoder.

### 2. Layout-Aware Chunking
* **Structural Chunking**: For PDFs, a `LayoutAwareDocumentChunker` splits structural data into logical chunks based on document hierarchy, section headings, and page limits.
* **Metadata Injection**: Each chunk is decorated with metadata headers for LLM readability:
  ```text
  Document: [Filename]
  Page: [Page Number]
  Section Path: [Hierarchy Path]
  ---
  [Content]
  ```
* **Sliding Window Fallback**: If a block exceeds token limits, a token-based sliding window strategy splits it to avoid clipping context.

### 3. Asynchronous Embedding Generation
* **Database Outbox/Polling**: After chunking, the document transitions to `ready_for_embedding`.
* **EmbeddingWorker**: A continuous background daemon polls for files in this state, changing their status to `embedding_running` during execution.
* **MockEmbeddingAdapter**: Generates deterministic, normalized pseudo-random unit vectors using SHA-256 hashes of the text salted with the model name. This produces stable unit Gaussian vectors to support local cosine similarity testing and vector search validation without third-party API dependencies.

---

## 🏗️ System Architecture

The application is built on a modern, separated architecture:

### 1. 🐍 Backend API (`backendPY/`)
A high-throughput REST API built with **FastAPI**.
* **Database Layer**: Uses SQLAlchemy ORM and Alembic for robust database migrations (SQLite/PostgreSQL ready).
* **PyMuPDF (`fitz`)**: Parses digital PDFs instantly and renders pages into high-fidelity preview PNGs.
* **PaddleOCR (v3.2.2)**: Performs high-accuracy optical character recognition (OCR) on scanned PDFs or raw images.
* **Auth**: Secure JWT (JSON Web Token) authentication flow for user sessions and password hashing.
* **Workers**: Run asynchronous task processing loops for embeddings and outbox messages.

### 2. ⚛️ Frontend Client (`frontend/`)
An interactive, single-page application focused on premium SaaS aesthetics.
* **React 18 + Vite + TypeScript**: Lightning-fast hot-reloading and robust type safety.
* **TailwindCSS & Shadcn UI**: Utility-first styling combined with highly accessible, customizable UI components (Radix UI).
* **Framer Motion**: Smooth micro-animations and visual transitions.

---

## 🚀 Installation & Local Setup

Follow these steps to set up and run both the backend and frontend services on your local machine.

### 📋 Prerequisites
* **Python**: v3.10 to v3.12 (v3.12 Recommended)
* **Node.js**: v18.0 or higher
* **Git**

---

### ⚙️ 1. Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backendPY
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: This locks `paddlepaddle==3.2.2` to ensure stability and compatibility with CPU hardware vectorization.*

4. **Run Database Migrations**:
   ```bash
   alembic upgrade head
   ```

5. **Start the FastAPI server**:
   ```bash
   python -m uvicorn main:app --reload
   ```
   * The backend will run on: **[http://localhost:8000](http://localhost:8000)**.
   * Interactive API docs (Swagger) available at: **[http://localhost:8000/docs](http://localhost:8000/docs)**.

---

### 🎨 2. Frontend Setup

1. **Open a new terminal and navigate to the frontend directory**:
   ```bash
   cd frontend
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

## ⚡ Performance Optimizations

* **oneDNN/MKLDNN Hardware Acceleration**: Configured `enable_mkldnn=True` in the PaddleOCR pipeline on CPU. This compiles matrix math operations to hardware vector instructions, yielding a **4x to 5x speed boost**.
* **Pre-empted Preprocessors**: Bypassed document layout classifiers, unwarp checking, and textline orientation directly inside the `PaddleOCR` class constructor. This reduces cold-start load time from **13.2 seconds** down to **1.5 seconds**.
* **Model Versioning**: Uses lightweight `PP-OCRv4` mobile inference models, keeping memory usage minimal.
* **Auto-unregistration Script**: Automatically clears stale PWA service workers on port `5173` to prevent blank white screens during project hot-swaps.

---

## 🗃️ Version Control & Contribution
* **Exclusions**: The `.gitignore` at the workspace root ensures that the virtual environment (`venv/`), static client-side build files (`dist/`), packages (`node_modules/`), and user uploaded documents under `backendPY/uploads/` are never committed to the remote repository.
* **Component Modularity**: UI components (like the bespoke `Tooltip` system and `LogoutButton`) are highly decoupled, ensuring easy maintenance and iteration.
