import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, ChevronLeft, ChevronRight, Copy, Check, FileText, LayoutDashboard } from "lucide-react";
import type { ExtractedDocument } from "@/lib/mockApi";
// import { MedicalReportView } from "./MedicalReportView";

interface TextPanelProps {
  document: ExtractedDocument;
  currentPage: number;
  onPageChange: (page: number) => void;
}

type Tab = "text" | "report";

export function TextPanel({ document, currentPage, onPageChange }: TextPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>("text");
  const [searchQuery, setSearchQuery] = useState("");
  const [copied, setCopied] = useState(false);
  const totalPages = document.pages.length;

  const currentText = document.pages[currentPage - 1]?.text || "";

  const highlightedText = useMemo(() => {
    if (!searchQuery.trim()) return currentText;

    const regex = new RegExp(`(${searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return currentText.replace(regex, '<mark class="bg-primary/30 text-foreground rounded px-0.5">$1</mark>');
  }, [currentText, searchQuery]);

  const matchCount = useMemo(() => {
    if (!searchQuery.trim()) return 0;
    const regex = new RegExp(searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
    return (currentText.match(regex) || []).length;
  }, [currentText, searchQuery]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(currentText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: 0.1, ease: [0.23, 1, 0.32, 1] }}
      className="h-full flex flex-col bg-card rounded-2xl border border-border shadow-soft overflow-hidden"
    >
      {/* Header with Tabs */}
      <div className="p-4 border-b border-border bg-muted/20">
        <div className="flex items-center justify-between mb-4">
          {/*
          <div className="flex bg-muted p-1 rounded-xl">
            <button
              onClick={() => setActiveTab("report")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${activeTab === "report"
                  ? "bg-background text-primary shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
                }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5" />
              Structured Report
            </button>
            <button
              onClick={() => setActiveTab("text")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${activeTab === "text"
                  ? "bg-background text-primary shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
                }`}
            >
              <FileText className="w-3.5 h-3.5" />
              Raw Text
            </button>
          </div>
          */}

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleCopy}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-muted hover:bg-muted/80 transition-colors"
          >
            <AnimatePresence mode="wait">
              {copied ? (
                <motion.span
                  key="copied"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="flex items-center gap-1 text-primary"
                >
                  <Check className="w-3.5 h-3.5" />
                  Copied
                </motion.span>
              ) : (
                <motion.span
                  key="copy"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="flex items-center gap-1 text-muted-foreground"
                >
                  <Copy className="w-3.5 h-3.5" />
                  Copy
                </motion.span>
              )}
            </AnimatePresence>
          </motion.button>
        </div>

        {/* Search (only for raw text) */}
        {activeTab === "text" && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search in text..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-muted border border-transparent focus:border-primary/50 focus:bg-background outline-none transition-all text-sm"
            />
            <AnimatePresence>
              {searchQuery && (
                <motion.span
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground bg-background px-2 py-0.5 rounded-full"
                >
                  {matchCount} {matchCount === 1 ? "match" : "matches"}
                </motion.span>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4 custom-scrollbar">
        <AnimatePresence mode="wait">
          {activeTab === "text" && (
            <motion.div
              key="text"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
              className="prose prose-sm max-w-none"
            >
              <p
                className="text-foreground leading-relaxed whitespace-pre-wrap"
                dangerouslySetInnerHTML={{ __html: highlightedText }}
              />
            </motion.div>
          )}

          {/* Commented out structured report view for later use
          {activeTab === "report" && (
            <motion.div
              key="report"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
            >
              {document.structuredData ? (
                <MedicalReportView data={document.structuredData} />
              ) : (
                <div className="h-full flex flex-col items-center justify-center p-12 text-center">
                  <LayoutDashboard className="w-12 h-12 text-muted-foreground mb-4 opacity-20" />
                  <p className="text-muted-foreground">No structured data available for this document.</p>
                </div>
              )}
            </motion.div>
          )}
          */}
        </AnimatePresence>
      </div>

      {/* Page navigation (only for raw text or multi-page docs) */}
      <div className="p-4 bg-muted/30 border-t border-border/50">
        <div className="flex items-center justify-between max-w-sm mx-auto bg-background/80 backdrop-blur-md border border-border/50 rounded-2xl p-1.5 shadow-lg">
          <button
            onClick={() => onPageChange(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className="p-2 rounded-xl hover:bg-muted disabled:opacity-20 transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2 px-4">
            <span className="text-sm font-bold text-primary">{currentPage}</span>
            <span className="text-xs text-muted-foreground font-medium">/</span>
            <span className="text-xs text-muted-foreground font-medium">{totalPages}</span>
          </div>

          <button
            onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
            className="p-2 rounded-xl hover:bg-muted disabled:opacity-20 transition-colors"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </motion.div>
  );
}

