import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileDropzone, type SelectedDocument } from "@/components/FileDropzone";
import { DocumentViewer } from "@/components/DocumentViewer";
import { TextPanel } from "@/components/TextPanel";
import { ErrorMessage } from "@/components/ErrorMessage";
import { EmptyState } from "@/components/EmptyState";
import { uploadDocument, type ExtractedDocument } from "@/lib/mockApi";
import { Sparkles } from "lucide-react";

const Index = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<SelectedDocument | null>(null);
  const [document, setDocument] = useState<ExtractedDocument | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = useCallback(async (selectedDoc: SelectedDocument) => {
    setSelectedFile(selectedDoc.file);
    setSelectedDocument(selectedDoc);
    setError(null);
    setIsLoading(true);
    setDocument(null);
    setCurrentPage(1);

    try {
      const result = await uploadDocument(selectedDoc.file);

      // Check if image/document has no readable text
      const hasText = result.pages.some(page => page.text && page.text.trim().length > 0);
      if (!hasText) {
        setError("Unable to extract text from this image. Please ensure the image contains readable text.");
        setIsLoading(false);
        return;
      }

      // Use the results directly from the backend
      setDocument(result);
    } catch (err) {

      setError(err instanceof Error ? err.message : "An unknown error occurred");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleClear = useCallback(() => {
    setSelectedFile(null);
    setDocument(null);
    setError(null);
    setCurrentPage(1);
  }, []);

  const handleRetry = useCallback(() => {
    if (selectedDocument) {
      handleFileSelect(selectedDocument);
    }
  }, [selectedDocument, handleFileSelect]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
        className="border-b border-border bg-card/50 backdrop-blur-xl sticky top-0 z-50"
      >
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center gap-3">
            <motion.div
              whileHover={{ scale: 1.05, rotate: 5 }}
              className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center"
            >
              <Sparkles className="w-5 h-5 text-primary-foreground" />
            </motion.div>
            <div>
              <h1 className="text-lg font-semibold text-foreground">DocExtract</h1>
              <p className="text-xs text-muted-foreground">AI-Powered Text Extraction</p>
            </div>
          </div>
        </div>
      </motion.header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <AnimatePresence mode="wait">
          {!document ? (
            <motion.div
              key="upload"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="max-w-2xl mx-auto space-y-6"
            >
              {/* Title */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="text-center mb-8"
              >
                <h2 className="text-3xl font-bold text-foreground mb-3">
                  Extract Text from Documents
                </h2>
                <p className="text-muted-foreground max-w-md mx-auto">
                  Upload PDFs or images and instantly extract text with our AI-powered OCR engine.
                </p>
              </motion.div>

              {/* File dropzone */}
              <FileDropzone
                onFileSelect={handleFileSelect}
                isLoading={isLoading}
                selectedFile={selectedFile}
                onClear={handleClear}
              />

              {/* Error message */}
              <AnimatePresence>
                {error && (
                  <ErrorMessage message={error} onRetry={handleRetry} />
                )}
              </AnimatePresence>

              {/* Features */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="grid grid-cols-3 gap-4 pt-8"
              >
                {[
                  { title: "Fast Processing", desc: "Extract in seconds" },
                  { title: "Multi-Page Support", desc: "Handle PDFs with ease" },
                  { title: "Smart Search", desc: "Find text instantly" },
                ].map((feature, idx) => (
                  <motion.div
                    key={feature.title}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 + idx * 0.1 }}
                    className="text-center p-4 rounded-xl bg-muted/50"
                  >
                    <p className="font-medium text-foreground text-sm">{feature.title}</p>
                    <p className="text-xs text-muted-foreground mt-1">{feature.desc}</p>
                  </motion.div>
                ))}
              </motion.div>
            </motion.div>
          ) : (
            <motion.div
              key="viewer"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
              className="space-y-6"
            >
              {/* Back button and title */}
              <div className="flex items-center justify-between">
                <motion.button
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  whileHover={{ x: -3 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleClear}
                  className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  <span>←</span>
                  <span>Upload New Document</span>
                </motion.button>
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.2 }}
                  className="text-sm text-muted-foreground"
                >
                  {document.pages.length} page{document.pages.length > 1 ? "s" : ""} extracted
                </motion.div>
              </div>

              {/* Split view */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-[600px]">
                <DocumentViewer document={document} currentPage={currentPage} />
                <TextPanel
                  document={document}
                  currentPage={currentPage}
                  onPageChange={setCurrentPage}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
};

export default Index;
