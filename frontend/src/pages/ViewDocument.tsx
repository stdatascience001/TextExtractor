import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { DocumentViewer } from "../components/DocumentViewer";
import { TextPanel } from "../components/TextPanel";
import { useToast } from "../components/ui/use-toast";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, ArrowLeft, Download, FileText, Code, Table } from "lucide-react";
import { ExtractedDocument } from "../lib/mockApi";
import { Tooltip } from "../components/ui/Tooltip";

export default function ViewDocument() {
  const { id } = useParams<{ id: string }>();
  const [documentData, setDocumentData] = useState<ExtractedDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  useEffect(() => {
    if (isAuthLoading) return;

    if (!isAuthenticated) {
      navigate("/login");
      return;
    }

    if (id) {
      fetchDocument(id);
    }
  }, [id, isAuthenticated, isAuthLoading, navigate]);

  const fetchDocument = async (docId: string) => {
    setLoading(true);
    try {
      const data = await api.getDocument(docId);
      
      // Transform backend DocumentResponse into frontend ExtractedDocument format
      const formattedData: ExtractedDocument = {
        fileType: data.file_type as "pdf" | "image",
        fileName: data.file_name,
        fileUrl: data.file_path,
        fullText: data.result?.full_text || "",
        structuredData: data.result?.structured_data || undefined,
        pages: [] // We simulate the pages array based on full text or empty for now
      };

      // Since the backend doesn't store per-page text breakdown yet, 
      // we'll pack the full text into page 1 for the viewer.
      formattedData.pages = [{
        pageNumber: 1,
        text: data.result?.full_text || "",
        imageUrl: data.file_type === "image" ? data.file_path : undefined
      }];

      setDocumentData(formattedData);
    } catch (err: any) {
      toast({ variant: "destructive", title: "Error", description: err.message || "Failed to load document" });
      navigate("/my-documents");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: "text" | "json" | "csv") => {
    if (!id) return;
    try {
      await api.exportDocument(id, format);
      toast({ title: "Export Started", description: `Downloading your ${format.toUpperCase()} file...` });
    } catch (err: any) {
      toast({ variant: "destructive", title: "Export Failed", description: err.message || "Failed to download document" });
    }
  };

  if (loading || isAuthLoading) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <header className="border-b border-border bg-card/50 backdrop-blur-xl p-4">
          <div className="max-w-[115rem] mx-auto animate-pulse flex h-6 w-32 bg-muted rounded"></div>
        </header>
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  if (!documentData) return null;

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-[115rem] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Tooltip title="Back to Dashboard" placement="bottom">
              <Link to="/my-documents" className="p-2 -ml-2 text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-muted">
                <ArrowLeft className="w-5 h-5" />
              </Link>
            </Tooltip>
            <div>
              <h1 className="text-lg font-semibold text-foreground truncate max-w-xs md:max-w-md lg:max-w-lg">
                {documentData.fileName}
              </h1>
              <p className="text-xs text-muted-foreground uppercase">{documentData.fileType} Document</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <Tooltip
              title="Export as Text"
              description="Download plain text without formatting."
              placement="bottom"
            >
              <button
                onClick={() => handleExport("text")}
                className="flex items-center gap-2 px-3 py-1.5 bg-muted/50 hover:bg-muted text-sm font-medium rounded-lg transition-colors border border-border"
              >
                <FileText className="w-4 h-4 text-primary" /> TXT
              </button>
            </Tooltip>
            
            <Tooltip
              title="Export as JSON"
              description="Structured data suitable for APIs and integrations."
              placement="bottom"
              shortcut="⌘+J"
            >
              <button
                onClick={() => handleExport("json")}
                className="flex items-center gap-2 px-3 py-1.5 bg-muted/50 hover:bg-muted text-sm font-medium rounded-lg transition-colors border border-border"
              >
                <Code className="w-4 h-4 text-primary" /> JSON
              </button>
            </Tooltip>

            <Tooltip
              title="Export as CSV"
              description="Tabular data ready for Excel or spreadsheets."
              placement="bottom"
            >
              <button
                onClick={() => handleExport("csv")}
                className="flex items-center gap-2 px-3 py-1.5 bg-muted/50 hover:bg-muted text-sm font-medium rounded-lg transition-colors border border-border"
              >
                <Table className="w-4 h-4 text-primary" /> CSV
              </button>
            </Tooltip>
          </div>
        </div>
      </header>

      <main className="max-w-[115rem] mx-auto px-6 py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Split view */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-[600px]">
            <DocumentViewer document={documentData} currentPage={currentPage} />
            <TextPanel
              document={documentData}
              currentPage={currentPage}
              onPageChange={setCurrentPage}
            />
          </div>
        </motion.div>
      </main>
    </div>
  );
}
