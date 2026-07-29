# DocExtract - AI-Powered Text Extraction Frontend

This is the React + TypeScript frontend application for **DocExtract**, a high-performance web interface designed for split-screen document rendering and text extraction verification.

![DocExtract Demo](public/FinalGIF.gif)

---

## ✨ Features

* **Drag-and-Drop Uploader**: Easily upload PDFs (`.pdf`) or images (`.png`, `.jpg`, `.jpeg`) using a smooth, animated dropzone.
* **Split-Screen Layout**:
  * **Left Panel**: Interactive document previewer displaying page-by-page images generated dynamically by the backend.
  * **Right Panel**: Extracted raw text panel.
* **Inline Word Search**: Real-time text search highlighting matches within the extracted text layout using occurrence counting.
* **Quick Copy**: One-click text copier with feedback animations.
* **Self-Healing Port Conflict Handler**: Auto-unregisters stale or cached PWA Service Workers on port `5173` from other projects, preventing blank screens.

---

## 🛠️ Technology Stack

* **Core**: [React 18](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/)
* **Build System**: [Vite](https://vitejs.dev/) (with SWC compiler for instant HMR)
* **Styling**: [TailwindCSS](https://tailwindcss.com/) + [Framer Motion](https://www.framer.com/motion/) (smooth micro-interactions)
* **Icons**: [Lucide React](https://lucide.dev/)

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have [Node.js](https://nodejs.org/) (v18 or higher) and `npm` installed.

### 2. Installation
Navigate to the frontend folder and install packages:
```bash
cd D:\Paras0218\PdfReader\frontend
npm install
```

### 3. Start Development Server
Launch the Vite local server:
```bash
npm run dev
```
The application will be accessible at: **[http://localhost:5173](http://localhost:5173)**.

---

## 🔗 Backend API Integration

The frontend communicates with the Python FastAPI backend via the endpoint configured in:
* **[src/lib/mockApi.ts](src/lib/mockApi.ts)**:
  ```typescript
  const API_URL = 'http://localhost:8000';
  ```
Ensure your FastAPI server is running on port `8000` before uploading files.

---