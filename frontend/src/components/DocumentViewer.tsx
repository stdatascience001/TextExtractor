import { motion, AnimatePresence } from "framer-motion";
import { FileText, Image as ImageIcon, AlertTriangle } from "lucide-react";
import type { ExtractedDocument } from "@/lib/mockApi";
import { SpreadsheetRenderer } from "./document_renderer/SpreadsheetRenderer";

interface DocumentViewerProps {
  document: ExtractedDocument;
  currentPage: number;
  onPageChange?: (page: number) => void;
}

export function DocumentViewer({
  document,
  currentPage,
  onPageChange,
}: DocumentViewerProps) {
  const currentPageData = document.pages[currentPage - 1];
  
  // Ensure we use the absolute URL for the backend API
  const getAbsoluteUrl = (url: string) => {
    if (!url) return "";
    return url.startsWith("http") ? url : `http://127.0.0.1:8000${url}`;
  };

  const fileUrl = getAbsoluteUrl(document.fileUrl);
  const imageUrl = currentPageData?.imageUrl ? getAbsoluteUrl(currentPageData.imageUrl) : fileUrl;
  const isPdf = document.fileType === "pdf" || document.fileName.toLowerCase().endsWith(".pdf");
  const isImage = document.fileType === "image" || [".jpg", ".jpeg", ".png"].some(ext => document.fileName.toLowerCase().endsWith(ext));
  const isSpreadsheet = document.fileType === "spreadsheet" || [".xlsx", ".xls", ".csv"].some(ext => document.fileName.toLowerCase().endsWith(ext));

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="h-full flex flex-col gap-4"
    >
      {/* ===== Preview Section ===== */}
      <div className="flex-1 relative rounded-xl overflow-hidden bg-surface-sunken border border-border">
        <AnimatePresence mode="wait">
          {isPdf ? (
            <motion.iframe
              key={`${fileUrl}-${currentPage}`}
              src={`${fileUrl}#page=${currentPage}&view=FitH`}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.02 }}
              transition={{ duration: 0.3 }}
              className="w-full h-full border-none"
              title={`${document.fileName} - PDF Preview`}
            />
          ) : isImage ? (
            <motion.img
              key={imageUrl}
              src={imageUrl}
              alt={`${document.fileName} - Page ${currentPage}`}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.02 }}
              transition={{ duration: 0.3 }}
              className="w-full h-full object-contain"
            />
          ) : isSpreadsheet ? (
            <motion.div
              key="spreadsheet-preview"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.02 }}
              transition={{ duration: 0.3 }}
              className="w-full h-full"
            >
              <SpreadsheetRenderer 
                document={document} 
                currentPage={currentPage} 
                onPageChange={onPageChange}
              />
            </motion.div>
          ) : (
            <motion.div
              key="text-preview"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.02 }}
              transition={{ duration: 0.3 }}
              className="w-full h-full bg-muted/20 p-6 overflow-y-auto flex justify-center"
            >
              <div className="w-full max-w-2xl bg-card shadow-soft rounded-lg border border-border p-6 min-h-[90%] text-foreground font-sans text-xs whitespace-pre-wrap leading-relaxed select-text">
                {currentPageData?.text || "No text content extracted for this page."}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* File name and page badge */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-full bg-foreground/80 backdrop-blur-sm border border-white/10 flex items-center gap-2">
          <span className="text-sm font-medium text-background">
            {document.fileName}
          </span>
          <span className="w-1 h-1 rounded-full bg-background/50" />
          <span className="text-xs font-bold text-background/80">
            PAGE {currentPage}
          </span>
        </div>
      </div>

    </motion.div>
  );
}
