import React, { createContext, useContext, useState, useMemo } from "react";

export interface BlockItem {
  id: string;
  block_id: string;
  document_id: string;
  page_number: number;
  parent_block_id: string | null;
  type: string;
  text: string;
  bbox: [number, number, number, number] | null;
  reading_order: number;
  heading_level: number | null;
  confidence: number;
  source_parser: string;
  created_at: string;
  metadata: any;
  image_path: string | null;
  table_html: string | null;
  children: BlockItem[];
}

export interface PageInfo {
  page_number: number;
  width: number;
  height: number;
  items: BlockItem[];
  image_path?: string;
}

export interface ExtractedDocument {
  fileType: "pdf" | "image" | "docx" | "text";
  fileName: string;
  fileUrl: string;
  status: string;
  fullText: string;
  structuredData?: {
    document?: {
      metadata?: any;
      pages?: PageInfo[];
    };
  };
  pages: {
    pageNumber: number;
    text: string;
    imageUrl?: string;
    items?: BlockItem[];
  }[];
}

interface DocumentContextType {
  document: ExtractedDocument | null;
  currentPage: number;
  selectedBlockId: string | null;
  searchQuery: string;
  highlightedBlockIds: string[];
  interactiveMode: "native" | "interactive";
  
  setDocument: (doc: ExtractedDocument | null) => void;
  setCurrentPage: (page: number) => void;
  setSelectedBlockId: (id: string | null) => void;
  setSearchQuery: (query: string) => void;
  setInteractiveMode: (mode: "native" | "interactive") => void;
  
  // Helpers
  selectBlock: (blockId: string, pageNumber: number) => void;
  clearSearch: () => void;
}

const DocumentContext = createContext<DocumentContextType | undefined>(undefined);

export const useDocumentContext = () => {
  const context = useContext(DocumentContext);
  if (!context) {
    throw new Error("useDocumentContext must be used within a DocumentProvider");
  }
  return context;
};

export const DocumentProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [document, setDocument] = useState<ExtractedDocument | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [interactiveMode, setInteractiveMode] = useState<"native" | "interactive">("native");

  // Helper to traverse tree and collect block matches
  const highlightedBlockIds = useMemo(() => {
    if (!searchQuery.trim() || !document) return [];
    
    const query = searchQuery.toLowerCase();
    const matches: string[] = [];

    const traverse = (item: BlockItem) => {
      if (item.text && item.text.toLowerCase().includes(query)) {
        matches.push(item.block_id);
      }
      if (item.children) {
        item.children.forEach(traverse);
      }
    };

    const pages = document.structuredData?.document?.pages || [];
    pages.forEach(page => {
      if (page.items) {
        page.items.forEach(traverse);
      }
    });

    return matches;
  }, [searchQuery, document]);

  const selectBlock = (blockId: string, pageNumber: number) => {
    setSelectedBlockId(blockId);
    setCurrentPage(pageNumber);
    setInteractiveMode("interactive"); // Auto-switch to show highlights
  };

  const clearSearch = () => {
    setSearchQuery("");
  };

  return (
    <DocumentContext.Provider
      value={{
        document,
        currentPage,
        selectedBlockId,
        searchQuery,
        highlightedBlockIds,
        interactiveMode,
        setDocument,
        setCurrentPage,
        setSelectedBlockId,
        setSearchQuery,
        setInteractiveMode,
        selectBlock,
        clearSearch
      }}
    >
      {children}
    </DocumentContext.Provider>
  );
};
