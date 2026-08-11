import React from 'react';
import { motion } from 'framer-motion';
import { FileText, ExternalLink } from 'lucide-react';

interface Citation {
  document_id: string;
  document_name: string;
  page_number: number;
  heading?: string;
  snippet: string;
  similarity_score?: number;
  confidence?: number;
  bounding_box?: number[];
}

interface CitationCardProps {
  citation: Citation;
  onClick: () => void;
  isActive?: boolean;
}

export function CitationCard({ citation, onClick, isActive = false }: CitationCardProps) {
  return (
    <motion.button
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.2 }}
        onClick={onClick}
        title={`${citation.document_name} - Page ${citation.page_number}`}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
          isActive
            ? 'border-primary bg-primary/10 text-primary shadow-sm font-semibold'
            : 'border-border bg-card text-muted-foreground hover:text-foreground hover:bg-muted/50 hover:border-slate-300'
        }`}
      >
        <FileText className="h-3 w-3 shrink-0" />
        <span>Page {citation.page_number}</span>
        <ExternalLink className="h-3 w-3 shrink-0 opacity-60 ml-0.5" />
      </motion.button>
  );
}

interface CitationListProps {
  citations: Citation[];
  onCitationClick: (citation: Citation) => void;
  activeCitation?: Citation;
}

export function CitationList({ citations, onCitationClick, activeCitation }: CitationListProps) {
  if (citations.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-2 mt-2" role="list" aria-label="Citations list">
      <span className="text-xs font-semibold text-muted-foreground mr-1">
        Sources:
      </span>
      {citations.map((citation, index) => (
        <CitationCard
          key={`${citation.document_id}-${citation.page_number}-${index}`}
          citation={citation}
          onClick={() => onCitationClick(citation)}
          isActive={
            activeCitation?.document_id === citation.document_id &&
            activeCitation?.page_number === citation.page_number
          }
        />
      ))}
    </div>
  );
}