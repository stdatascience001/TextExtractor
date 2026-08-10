import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Search, FileText, Zap, CheckCircle2 } from 'lucide-react';

type SearchStep = 'searching' | 'finding' | 'ranking' | 'building' | 'generating' | 'citations' | 'done';

interface SearchStatusProps {
  currentStep: SearchStep;
  documentCount?: number;
}

const steps: Record<SearchStep, { icon: React.ReactNode; label: string }> = {
  searching: { icon: <Search className="h-4 w-4" />, label: 'Searching documents...' },
  finding: { icon: <FileText className="h-4 w-4" />, label: 'Finding relevant pages...' },
  ranking: { icon: <Loader2 className="h-4 w-4 animate-spin" />, label: 'Ranking results...' },
  building: { icon: <Zap className="h-4 w-4" />, label: 'Building context...' },
  generating: { icon: <Loader2 className="h-4 w-4 animate-spin" />, label: 'Generating answer...' },
  citations: { icon: <FileText className="h-4 w-4" />, label: 'Receiving citations...' },
  done: { icon: <CheckCircle2 className="h-4 w-4" />, label: 'Done' },
};

export function SearchStatus({ currentStep, documentCount = 0 }: SearchStatusProps) {
  const stepOrder: SearchStep[] = ['searching', 'finding', 'ranking', 'building', 'generating', 'citations', 'done'];
  const currentIndex = stepOrder.indexOf(currentStep);

  return (
    <AnimatePresence mode="wait">
      {currentStep !== 'done' && (
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3 }}
          className="flex items-center gap-3 px-4 py-3 text-sm text-muted-foreground"
        >
          <div className="text-primary">
            {steps[currentStep].icon}
          </div>
          <span>{steps[currentStep].label}</span>
          {documentCount > 0 && currentStep === 'searching' && (
            <span className="text-xs">({documentCount} documents)</span>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}