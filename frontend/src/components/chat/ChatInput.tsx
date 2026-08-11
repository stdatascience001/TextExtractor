import React, { useState, useRef, useEffect, forwardRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Paperclip, X, Mic, MicOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
  suggestedQuestions?: string[];
  onSuggestedQuestionClick?: (question: string) => void;
}

export const ChatInput = forwardRef<HTMLTextAreaElement, ChatInputProps>(({
  value,
  onChange,
  onSend,
  disabled = false,
  placeholder = 'Ask a question about this document...',
  maxLength = 4000,
  suggestedQuestions = [],
  onSuggestedQuestionClick,
}, ref) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Use forwarded ref or local ref
  const setRef = (node: HTMLTextAreaElement | null) => {
    textareaRef.current = node;
    if (typeof ref === 'function') {
      ref(node);
    } else if (ref) {
      ref.current = node;
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) {
        onSend();
      }
    }
  };

  const handlePaste = async (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (const item of items) {
      if (item.type.indexOf('image') !== -1) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) {
          toast.info('Image paste detected - file upload feature coming soon');
        }
      }
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      toast.info(`File drop detected - ${files.length} file(s) upload feature coming soon`);
    }
  };

  const handleSuggestionClick = (question: string) => {
    onChange(question);
    setShowSuggestions(false);
    onSuggestedQuestionClick?.(question);
  };

  const characterCount = value.length;
  const isNearLimit = characterCount > maxLength * 0.9;

  return (
    <div className="relative">
      {/* Suggested Questions */}
      <AnimatePresence>
        {showSuggestions && suggestedQuestions.length > 0 && value === '' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="absolute bottom-full left-0 right-0 mb-2 p-3 bg-muted rounded-lg border border-border"
          >
            <p className="text-xs font-medium text-muted-foreground mb-2">
              Try asking:
            </p>
            <div className="space-y-1">
              {suggestedQuestions.slice(0, 3).map((question) => (
                <button
                  key={question}
                  onClick={() => handleSuggestionClick(question)}
                  className="w-full text-left text-sm p-2 rounded hover:bg-background transition-colors"
                >
                  {question}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input Container */}
      <div
        className={`relative border border-border rounded-xl flex items-center px-3 py-2 transition-all ${
          isDragging
            ? 'border-primary bg-primary/5'
            : 'bg-background hover:border-slate-300 focus-within:border-primary focus-within:ring-1 focus-within:ring-primary/20'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-foreground shrink-0"
            disabled={disabled}
            onClick={() => toast.info('File attachment feature coming soon')}
            aria-label="Attach file"
          >
            <Paperclip className="h-4 w-4" />
          </Button>

        <Textarea
          ref={setRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          onFocus={() => setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
          placeholder={placeholder}
          disabled={disabled}
          maxLength={maxLength}
          className="flex-1 min-h-[40px] max-h-[160px] py-1.5 px-3 resize-none border-0 focus-visible:ring-0 bg-transparent text-sm focus-visible:ring-offset-0 focus:outline-none"
          rows={1}
          aria-label="Chat input"
          aria-describedby="character-count"
        />

        {/* Action Buttons */}
        <div className="flex items-center gap-1.5 shrink-0">
          {value.length > 0 && (
            <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-muted-foreground hover:text-foreground"
                onClick={() => onChange('')}
                disabled={disabled}
                aria-label="Clear input"
              >
                <X className="h-4 w-4" />
              </Button>
          )}

          <Button
              size="sm"
              className="h-8 px-4 rounded-lg bg-primary hover:bg-primary/90 text-white font-medium text-xs shadow-sm transition-colors shrink-0"
              disabled={disabled || !value.trim()}
              onClick={onSend}
              aria-label="Send message"
            >
              send
            </Button>
        </div>
      </div>

      {/* Character Count & Drag Overlay */}
      <div className="flex items-center justify-between mt-1 px-1">
        <div className="text-xs text-muted-foreground">
          {isDragging && (
            <span className="text-primary">Drop files to upload</span>
          )}
        </div>
        {value.length > 0 && (
          <div 
            id="character-count"
            className={`text-xs ${isNearLimit ? 'text-destructive' : 'text-muted-foreground'}`}
          >
            {characterCount}/{maxLength}
          </div>
        )}
      </div>
    </div>
  );
});

ChatInput.displayName = 'ChatInput';