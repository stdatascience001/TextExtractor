import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, ChevronDown, FileText, Pin, Grid3x3 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';

interface Document {
  id: string;
  file_name: string;
  file_type: string;
  status: string;
}

interface DocumentSelectorProps {
  documents: Document[];
  selectedIds: Set<string>;
  onChange: (selectedIds: Set<string>) => void;
  disabled?: boolean;
}

export function DocumentSelector({
  documents,
  selectedIds,
  onChange,
  disabled = false,
}: DocumentSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleToggleDocument = (docId: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(docId)) {
      newSelected.delete(docId);
    } else {
      newSelected.add(docId);
    }
    onChange(newSelected);
  };

  const handleSelectAll = () => {
    const allIds = new Set(documents.map((doc) => doc.id));
    onChange(allIds);
  };

  const handleClearAll = () => {
    onChange(new Set());
  };

  const selectedCount = selectedIds.size;
  const totalCount = documents.length;

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          disabled={disabled || documents.length === 0}
          className="gap-2"
        >
          <FileText className="h-4 w-4" />
          <span>
            {selectedCount === 0
              ? 'Select Documents'
              : selectedCount === totalCount
              ? 'All Documents'
              : `${selectedCount} Document${selectedCount > 1 ? 's' : ''}`}
          </span>
          <ChevronDown className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-80 p-0">
        <div className="p-3 border-b border-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Documents</span>
            <Badge variant="secondary" className="text-xs">
              {selectedCount}/{totalCount}
            </Badge>
          </div>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="flex-1 h-7 text-xs"
              onClick={handleSelectAll}
              disabled={selectedCount === totalCount}
            >
              Select All
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="flex-1 h-7 text-xs"
              onClick={handleClearAll}
              disabled={selectedCount === 0}
            >
              Clear All
            </Button>
          </div>
        </div>

        <ScrollArea className="h-64">
          <div className="p-2">
            {documents.length === 0 ? (
              <div className="text-center py-8 text-sm text-muted-foreground">
                No documents available
              </div>
            ) : (
              documents.map((doc) => (
                <DropdownMenuItem
                  key={doc.id}
                  onSelect={(e) => e.preventDefault()}
                  onClick={() => handleToggleDocument(doc.id)}
                  className="flex items-center gap-3 p-2 cursor-pointer"
                >
                  <div className={`flex-shrink-0 w-5 h-5 rounded border flex items-center justify-center ${
                    selectedIds.has(doc.id)
                      ? 'bg-primary border-primary text-primary-foreground'
                      : 'border-border'
                  }`}>
                    {selectedIds.has(doc.id) && <Check className="h-3 w-3" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{doc.file_name}</p>
                    <p className="text-xs text-muted-foreground capitalize">{doc.file_type}</p>
                  </div>
                  {doc.status === 'completed' && (
                    <Badge variant="outline" className="text-xs">
                      Ready
                    </Badge>
                  )}
                </DropdownMenuItem>
              ))
            )}
          </div>
        </ScrollArea>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}