import React, { useState, useMemo } from "react";
import { useDocumentContext, PageInfo } from "./DocumentContext";
import { PageRenderer } from "./PageRenderer";
import { Search, ChevronLeft, ChevronRight, Copy, Check, FileText, LayoutDashboard } from "lucide-react";
import { Tooltip } from "../ui/Tooltip";
import { motion, AnimatePresence } from "framer-motion";

export const DocumentRenderer: React.FC = () => {
  const {
    document,
    currentPage,
    searchQuery,
    highlightedBlockIds,
    setCurrentPage,
    setSearchQuery
  } = useDocumentContext();

  const [activeTab, setActiveTab] = useState<"text" | "structured">("structured");
  const [copied, setCopied] = useState(false);

  const pages = document?.structuredData?.document?.pages || [];
  const activePageData = useMemo(() => {
    return pages.find((p) => p.page_number === currentPage) || null;
  }, [pages, currentPage]);

  const totalPages = pages.length || document?.pages?.length || 1;

  // Flattened text for raw text mode
  const currentRawText = useMemo(() => {
    if (activePageData) {
      const getBlockText = (item: any): string => {
        let text = item.text || "";
        if (item.children) {
          text += "\n" + item.children.map(getBlockText).join("\n");
        }
        return text;
      };
      return activePageData.items.map(getBlockText).filter(Boolean).join("\n\n");
    }
    return document?.pages[currentPage - 1]?.text || "";
  }, [activePageData, document, currentPage]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(currentRawText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const matchCount = useMemo(() => {
    if (!searchQuery.trim()) return 0;
    return highlightedBlockIds.length;
  }, [searchQuery, highlightedBlockIds]);

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: 0.1, ease: [0.23, 1, 0.32, 1] }}
      className="h-full flex flex-col bg-card rounded-2xl border border-border shadow-soft overflow-hidden"
    >
      {/* Tab controls */}
      <div className="p-4 border-b border-border bg-muted/20">
        <div className="flex items-center justify-between mb-4">
          <div className="flex bg-muted p-1 rounded-xl">
            <button
              onClick={() => setActiveTab("structured")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === "structured"
                  ? "bg-background text-primary shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5" />
              Structured Layout
            </button>
            <button
              onClick={() => setActiveTab("text")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === "text"
                  ? "bg-background text-primary shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              Raw Text
            </button>
          </div>

          <Tooltip title="Copy Text" description="Copy the active page's text to clipboard." placement="bottom">
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-muted hover:bg-muted/80 transition-colors"
            >
              {copied ? (
                <span className="flex items-center gap-1 text-primary">
                  <Check className="w-3.5 h-3.5" /> Copied
                </span>
              ) : (
                <span className="flex items-center gap-1 text-muted-foreground">
                  <Copy className="w-3.5 h-3.5" /> Copy
                </span>
              )}
            </button>
          </Tooltip>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search block elements..."
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
      </div>

      {/* Main View Area */}
      <div className="flex-1 overflow-auto p-4 custom-scrollbar">
        <AnimatePresence mode="wait">
          {activeTab === "structured" ? (
            <motion.div
              key="structured"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              {activePageData ? (
                <PageRenderer page={activePageData} />
              ) : (
                <p className="text-xs text-muted-foreground italic text-center py-12">
                  No layout blocks available for this page.
                </p>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="text"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="prose prose-sm max-w-none"
            >
              <p className="text-foreground leading-relaxed whitespace-pre-wrap">
                {currentRawText || "No text content identified on this page."}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Footer Page Navigation */}
      <div className="p-4 bg-muted/30 border-t border-border/50">
        <div className="flex items-center justify-between max-w-sm mx-auto bg-background/80 backdrop-blur-md border border-border/50 rounded-2xl p-1.5 shadow-lg">
          <Tooltip title="Previous Page" shortcut="←">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="p-2 rounded-xl hover:bg-muted disabled:opacity-20 transition-colors"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
          </Tooltip>

          <div className="flex items-center gap-2 px-4">
            <span className="text-sm font-bold text-primary">{currentPage}</span>
            <span className="text-xs text-muted-foreground font-medium">/</span>
            <span className="text-xs text-muted-foreground font-medium">{totalPages}</span>
          </div>

          <Tooltip title="Next Page" shortcut="→">
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="p-2 rounded-xl hover:bg-muted disabled:opacity-20 transition-colors"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </Tooltip>
        </div>
      </div>
    </motion.div>
  );
};
