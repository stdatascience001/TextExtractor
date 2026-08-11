import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileText, 
  Image as ImageIcon, 
  ChevronLeft, 
  ChevronRight, 
  Search, 
  X, 
  ZoomIn, 
  ZoomOut,
  Maximize2,
  Minimize2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';


interface Document {
  id: string;
  file_name: string;
  file_type: string;
  file_url?: string;
  pages?: Array<{
    page_number: number;
    image_url?: string;
    structured_text?: string;
    text?: string;
  }>;
}

interface CitationHighlight {
  document_id: string;
  page_number: number;
  bounding_box?: number[];
  snippet?: string;
}

interface DocumentViewerPanelProps {
  documents: Document[];
  selectedDocumentId: string | null;
  onDocumentSelect: (id: string) => void;
  citationHighlight: CitationHighlight | null;
  onHighlightClear: () => void;
}

export function DocumentViewerPanel({
  documents,
  selectedDocumentId,
  onDocumentSelect,
  citationHighlight,
  onHighlightClear,
}: DocumentViewerPanelProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [zoom, setZoom] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const selectedDocument = documents.find((doc) => doc.id === selectedDocumentId);
  const totalPages = selectedDocument?.pages?.length || 0;

  // Handle citation highlight navigation
  useEffect(() => {
    if (citationHighlight && citationHighlight.document_id === selectedDocumentId) {
      setCurrentPage(citationHighlight.page_number);
      setTimeout(() => {
        const pageElement = pageRefs.current[citationHighlight.page_number];
        if (pageElement) {
          pageElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 100);
    }
  }, [citationHighlight, selectedDocumentId]);

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.25, 3));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.25, 0.5));

  const getAbsoluteUrl = (url: string) => {
    if (!url) return '';
    return url.startsWith('http') ? url : `http://127.0.0.1:8000${url}`;
  };

  const isPdf = selectedDocument?.file_type === 'pdf' || selectedDocument?.file_name?.toLowerCase().endsWith('.pdf');
  const isImage = selectedDocument?.file_type === 'image' || ['.jpg', '.jpeg', '.png'].some(ext => selectedDocument?.file_name?.toLowerCase().endsWith(ext));

  if (!selectedDocument) {
    return (
      <div className="h-full flex items-center justify-center bg-muted/20">
        <div className="text-center">
          <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-sm text-muted-foreground">No document selected</p>
        </div>
      </div>
    );
  }

  const currentPageData = selectedDocument.pages?.[currentPage - 1];
  const fileUrl = selectedDocument.file_url ? getAbsoluteUrl(selectedDocument.file_url) : '';
  const imageUrl = currentPageData?.image_url ? getAbsoluteUrl(currentPageData.image_url) : fileUrl;

  return (
    <div className={`flex flex-col h-full bg-background ${isFullscreen ? 'fixed inset-0 z-50' : ''}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <FileText className="h-5 w-5 text-muted-foreground flex-shrink-0" />
          <div className="min-w-0">
            <p className="text-sm font-medium truncate">{selectedDocument.file_name}</p>
            {citationHighlight && (
              <Badge variant="outline" className="text-xs mt-1">
                Citation: Page {citationHighlight.page_number}
              </Badge>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Zoom Controls */}
          <div className="flex items-center gap-1 border-r border-border pr-2">
            <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={handleZoomOut}
                disabled={zoom <= 0.5}
                aria-label="Zoom Out"
                title="Zoom Out"
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
            <span className="text-xs font-medium w-12 text-center">{Math.round(zoom * 100)}%</span>
            <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={handleZoomIn}
                disabled={zoom >= 3}
                aria-label="Zoom In"
                title="Zoom In"
              >
                <ZoomIn className="h-4 w-4" />
              </Button>
          </div>

          {/* Fullscreen Toggle */}
          <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={() => setIsFullscreen(!isFullscreen)}
              aria-label={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
              title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
            >
              {isFullscreen ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>

          {citationHighlight && (
            <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={onHighlightClear}
                aria-label="Clear Highlight"
                title="Clear Highlight"
              >
                <X className="h-4 w-4" />
              </Button>
          )}
        </div>
      </div>

      {/* Document Content */}
      <ScrollArea className="flex-1 min-h-0">
        <div 
          ref={containerRef}
          className="p-4 flex justify-center"
          style={{ transform: `scale(${zoom})`, transformOrigin: 'top center' }}
        >
          <div className="max-w-4xl w-full">
            {isPdf ? (
              <iframe
                key={currentPage}
                src={`${fileUrl}#page=${currentPage}&view=FitH`}
                className="w-full h-[800px] border rounded-lg"
                title={`${selectedDocument.file_name} - PDF Viewer`}
              />
            ) : isImage && imageUrl ? (
              <img
                src={imageUrl}
                alt={`${selectedDocument.file_name} - Page ${currentPage}`}
                className="w-full rounded-lg border"
              />
            ) : (
              <div
                ref={(el) => { pageRefs.current[currentPage] = el; }}
                className="bg-card border rounded-lg p-6 min-h-[600px]"
              >
                <div className="flex items-center justify-between mb-4">
                  <Badge variant="outline">Page {currentPage}</Badge>
                  {currentPageData?.structured_text && (
                    <Badge variant="secondary">Structured Text</Badge>
                  )}
                </div>
                <div className="prose prose-sm max-w-none whitespace-pre-wrap">
                  {currentPageData?.structured_text || currentPageData?.text || 'No text content available for this page.'}
                </div>
                
                {/* Citation Highlight */}
                {citationHighlight && citationHighlight.page_number === currentPage && citationHighlight.snippet && (
                  <motion.div
                    initial={{ opacity: 0, backgroundColor: 'rgba(59, 130, 246, 0)' }}
                    animate={{ opacity: 1, backgroundColor: 'rgba(59, 130, 246, 0.1)' }}
                    className="mt-4 p-4 rounded-lg border border-primary/30"
                  >
                    <p className="text-xs font-medium text-primary mb-2">Cited Text:</p>
                    <p className="text-sm italic">"{citationHighlight.snippet}"</p>
                  </motion.div>
                )}
              </div>
            )}
          </div>
        </div>
      </ScrollArea>

      {/* Footer - Page Navigation */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between p-4 border-t border-border flex-shrink-0 bg-background">
          <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage <= 1}
              title="Previous Page"
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Previous
            </Button>

          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              Page {currentPage} of {totalPages}
            </span>
            <div className="flex items-center gap-1">
              <Input
                type="number"
                min={1}
                max={totalPages}
                value={currentPage}
                onChange={(e) => handlePageChange(parseInt(e.target.value) || 1)}
                className="w-16 h-8 text-center"
              />
              <span className="text-sm text-muted-foreground">/ {totalPages}</span>
            </div>
          </div>

          <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage >= totalPages}
              title="Next Page"
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
        </div>
      )}
    </div>
  );
}