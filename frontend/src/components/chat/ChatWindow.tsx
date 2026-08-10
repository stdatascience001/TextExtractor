import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Square, Loader2, Keyboard } from 'lucide-react';
import { MessageBubble } from './MessageBubble';
import { StreamingMessage } from './StreamingMessage';
import { SearchStatus } from './SearchStatus';
import { SuggestedQuestions } from './SuggestedQuestions';
import { CitationList } from './CitationCard';
import { ChatInput } from './ChatInput';
import { AnswerModeSelector } from './AnswerModeSelector';
import { useKeyboardShortcuts, commonShortcuts } from './useKeyboardShortcuts';
import { toast } from 'sonner';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: Array<{
    document_id: string;
    document_name: string;
    page_number: number;
    heading?: string;
    snippet: string;
    similarity_score?: number;
    confidence?: number;
    bounding_box?: number[];
  }>;
  suggestedQuestions?: string[];
}

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

type SearchStep = 'idle' | 'searching' | 'finding' | 'ranking' | 'building' | 'generating' | 'citations' | 'done';

type AnswerMode =
  | 'summary'
  | 'detailed'
  | 'explain'
  | 'compare'
  | 'timeline'
  | 'bullet_points'
  | 'flashcards'
  | 'key_insights'
  | 'table'
  | 'json'
  | 'qa';

interface ChatWindowProps {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  searchStep: SearchStep;
  answerMode: AnswerMode;
  onAnswerModeChange: (mode: AnswerMode) => void;
  onSendMessage: (content: string) => void;
  onStopGeneration: () => void;
  onCitationClick: (citation: Citation) => void;
  onRegenerateMessage?: () => void;
  onCopyMessage?: (content: string) => void;
  disabled?: boolean;
  suggestedQuestions?: string[];
  onSuggestedQuestionClick?: (question: string) => void;
}

export function ChatWindow({
  messages,
  isStreaming,
  streamingContent,
  searchStep,
  answerMode,
  onAnswerModeChange,
  onSendMessage,
  onStopGeneration,
  onCitationClick,
  onRegenerateMessage,
  onCopyMessage,
  disabled = false,
  suggestedQuestions = [],
  onSuggestedQuestionClick,
}: ChatWindowProps) {
  const [inputValue, setInputValue] = useState('');
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Keyboard shortcuts
  useKeyboardShortcuts([
    {
      ...commonShortcuts.focusInput,
      handler: () => inputRef.current?.focus(),
    },
    {
      ...commonShortcuts.escape,
      handler: () => {
        if (isStreaming) {
          onStopGeneration();
        }
        inputRef.current?.blur();
      },
    },
  ]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const handleSend = () => {
    if (inputValue.trim() && !disabled) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  const handleCitationClick = (citation: Citation) => {
    setActiveCitation(citation);
    onCitationClick(citation);
  };

  const lastMessage = messages[messages.length - 1];
  const showSuggestions = !isStreaming && lastMessage?.role === 'assistant' && suggestedQuestions.length > 0;

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">Chat</h2>
          {isStreaming && (
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span className="text-sm text-muted-foreground">Generating response...</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0"
                onClick={onStopGeneration}
              >
                <Square className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
        <AnswerModeSelector
          value={answerMode}
          onChange={onAnswerModeChange}
          disabled={isStreaming || disabled}
        />
      </div>

      {/* Messages Area */}
      <ScrollArea ref={scrollAreaRef} className="flex-1 min-h-0">
        <div className="px-6 py-4 max-w-4xl mx-auto">
          {messages.length === 0 && !isStreaming ? (
            <div className="flex flex-col items-center justify-center h-full py-12">
              <div className="text-center max-w-md">
                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4"
                >
                  <span className="text-3xl">💬</span>
                </motion.div>
                <h3 className="text-lg font-semibold mb-2">Start a conversation</h3>
                <p className="text-sm text-muted-foreground">
                  Ask questions about this document and get answers with citations.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((message, index) => (
                <div key={index}>
                  <MessageBubble
                    role={message.role}
                    content={message.content}
                    onCopy={() => onCopyMessage?.(message.content)}
                    onRegenerate={message.role === 'assistant' ? onRegenerateMessage : undefined}
                  >
                    {message.role === 'assistant' ? (
                      <div className="prose prose-sm max-w-none prose-gray">
                        {message.content}
                      </div>
                    ) : (
                      <div className="text-sm">{message.content}</div>
                    )}
                  </MessageBubble>

                  {/* Citations for assistant messages */}
                  {message.role === 'assistant' && 
                   message.citations && 
                   message.citations.length > 0 && 
                   !message.content.includes("I couldn't find this information in the uploaded document.") && (
                    <div className="ml-11 mt-2">
                      <CitationList
                        citations={message.citations}
                        onCitationClick={handleCitationClick}
                        activeCitation={activeCitation}
                      />
                    </div>
                  )}

                  {/* Suggested questions after assistant messages */}
                  {message.role === 'assistant' && message.suggestedQuestions && message.suggestedQuestions.length > 0 && (
                    <div className="ml-11 mt-4">
                      <SuggestedQuestions
                        questions={message.suggestedQuestions}
                        onQuestionClick={(q) => {
                          onSuggestedQuestionClick?.(q);
                          setInputValue('');
                        }}
                      />
                    </div>
                  )}
                </div>
              ))}

              {/* Streaming Message */}
              {isStreaming && (
                <>
                  <SearchStatus currentStep={searchStep} />
                  {streamingContent && (
                    <StreamingMessage
                      content={streamingContent}
                      isComplete={false}
                    />
                  )}
                </>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="p-4 border-t border-border flex-shrink-0 bg-background">
        <div className="max-w-4xl mx-auto">
          <ChatInput
            ref={inputRef}
            value={inputValue}
            onChange={setInputValue}
            onSend={handleSend}
            disabled={disabled || isStreaming}
            suggestedQuestions={suggestedQuestions}
            onSuggestedQuestionClick={(q) => {
              setInputValue(q);
              onSuggestedQuestionClick?.(q);
            }}
          />
        </div>
      </div>
    </div>
  );
}