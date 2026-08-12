import { useState, useCallback, useEffect } from "react";

import { motion, AnimatePresence } from "framer-motion";
import { FileDropzone, type SelectedDocument } from "@/components/FileDropzone";
import { GoogleSheetImport } from "@/components/GoogleSheetImport";
import { DocumentViewer } from "@/components/DocumentViewer";
import { TextPanel } from "@/components/TextPanel";
import { ErrorMessage } from "@/components/ErrorMessage";
import { EmptyState } from "@/components/EmptyState";
import { uploadDocument, type ExtractedDocument } from "@/lib/mockApi";
import { Sparkles, Save, Loader2, LogOut, User as UserIcon } from "lucide-react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { LogoutButton } from "@/components/LogoutButton";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/use-toast";
import { SidebarLayout } from "@/shared/layouts/SidebarLayout";


const Index = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<SelectedDocument | null>(null);
  const [document, setDocument] = useState<ExtractedDocument | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const { user, isAuthenticated, setPendingDocument, logout } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  // Enforce project workspace entry point validation
  useEffect(() => {
    if (isAuthenticated) {
      const activeProj = localStorage.getItem("activeProjectId");
      if (!activeProj) {
        toast({
          title: "Project Context Required",
          description: "Please select or create a project context to begin document parsing.",
        });
        navigate("/projects");
      }
    }
  }, [isAuthenticated, navigate]);

  const handleSave = async () => {
    if (!document) return;

    if (!isAuthenticated) {
      setPendingDocument(document);
      toast({ title: "Authentication required", description: "Please log in to save documents." });
      navigate("/login");
      return;
    }

    const activeProjectId = localStorage.getItem("activeProjectId");
    if (!activeProjectId) {
      toast({ title: "Project Context Missing", description: "Please select a project to save this document.", variant: "destructive" });
      navigate("/projects");
      return;
    }

    setIsSaving(true);
    try {
      await api.saveDocument({
        file_name: document.fileName,
        file_type: document.fileType,
        file_path: document.fileUrl,
        full_text: document.fullText || "",
        structured_data: document.structuredData || null,
        project_id: activeProjectId
      });
      toast({ title: "Success", description: "Document saved successfully!" });
    } catch (err: any) {
      toast({ variant: "destructive", title: "Save failed", description: err.message });
    } finally {
      setIsSaving(false);
    }
  };

  const handleFileSelect = useCallback(async (selectedDoc: SelectedDocument) => {

    setSelectedFile(selectedDoc.file);
    setSelectedDocument(selectedDoc);
    setError(null);
    setIsLoading(true);
    setDocument(null);
    setCurrentPage(1);

    try {
      const result = await uploadDocument(selectedDoc.file);

      toast({
        title: "Upload Accepted",
        description: "Document processing queued in the background. Redirecting to document view page...",
      });

      setTimeout(() => {
        navigate(`/documents/${result.document_id}`);
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unknown error occurred");
      setIsLoading(false);
    }
  }, [navigate, toast]);

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
    <SidebarLayout>
      <div className="min-h-screen bg-background">
        {/* Header */}
        {!isAuthenticated && (
          <motion.header
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
            className="border-b border-border bg-card/50 backdrop-blur-xl sticky top-0 z-50"
          >
            <div className="max-w-[115rem] mx-auto px-6 py-4">
              <div className="flex items-center gap-3">
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  className="w-10 h-10 overflow-hidden flex items-center justify-center bg-card"
                >
                  <img src="/favicon1.png" alt="Logo" className="w-full h-full object-contain p-1" />
                </motion.div>
                <div>
                  <h1 className="text-lg font-semibold text-foreground">DocExtract</h1>
                  <p className="text-xs text-muted-foreground">AI-Powered Text Extraction</p>
                </div>
              </div>

              <div className="flex items-center gap-4">
                {isAuthenticated ? (
                  <div className="flex items-center gap-4">
                    <Link to="/my-documents" className="text-sm font-medium text-foreground hover:text-primary transition-colors">
                      My Documents
                    </Link>
                    <div className="h-4 w-px bg-border"></div>
                    <Link to="/profile" className="text-sm font-medium text-foreground hover:text-primary transition-colors flex items-center gap-2">
                      <UserIcon className="w-4 h-4" /> {user?.username}
                    </Link>
                    <LogoutButton
                      className="text-sm text-muted-foreground hover:text-red-800 cursor-pointer flex items-center gap-1 transition-colors"
                      showIcon
                    >
                      Logout
                    </LogoutButton>
                  </div>
                ) : (
                  <button
                    onClick={() => navigate("/login")}
                    className="text-sm font-medium text-primary hover:text-primary/80 transition-colors"
                  >
                    Sign In
                  </button>
                )}
              </div>
            </div>
          </motion.header>
        )}

        {/* Main content */}
        <main className="max-w-[115rem] mx-auto px-6 py-8">
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

                {/* Google Sheet Import */}
                <GoogleSheetImport />

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
                  <div className="flex items-center gap-4">
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.2 }}
                      className="text-sm text-muted-foreground"
                    >
                      {document.pages.length} page{document.pages.length > 1 ? "s" : ""} extracted
                    </motion.div>
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={handleSave}
                      disabled={isSaving}
                      className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
                    >
                      {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                      {isSaving ? "Saving..." : "Save Document"}
                    </motion.button>
                  </div>
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
    </SidebarLayout>
  );
};

export default Index;
