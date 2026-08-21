import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { ConversationSidebar } from './ConversationSidebar';
import { ChatWindow } from './ChatWindow';
import { DocumentViewerPanel } from './DocumentViewerPanel';
import { ResponsiveLayout } from './ResponsiveLayout';
import { api } from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';
import { toast } from 'sonner';

interface Document {
  id: string;
  file_name: string;
  file_type: string;
  file_url?: string;
  status: string;
  pages?: Array<{
    page_number: number;
    image_url?: string;
    structured_text?: string;
    text?: string;
  }>;
}

interface Conversation {
  conversation_id: string;
  title: string;
  status: string;
  summary?: string;
  selected_document_ids?: string[];
  created_at: string;
  is_pinned?: boolean;
  is_archived?: boolean;
}

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

export function AssistantWorkspace() {
  const { documentId } = useParams<{ documentId: string }>();
  const { toast: uiToast } = useToast();

  // Documents state
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<Set<string>>(new Set());
  const [loadingDocs, setLoadingDocs] = useState(true);

  // Conversations state
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [loadingConvs, setLoadingConvs] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showArchived, setShowArchived] = useState(false);

  // Messages state
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [searchStep, setSearchStep] = useState<SearchStep>('idle');
  const [answerMode, setAnswerMode] = useState<AnswerMode>('detailed');

  // Citation state
  const [citationHighlight, setCitationHighlight] = useState<{
    document_id: string;
    page_number: number;
    bounding_box?: number[];
    snippet?: string;
  } | null>(null);

  // Abort controller for streaming
  const abortControllerRef = useRef<AbortController | null>(null);

  // Load document workspace
  useEffect(() => {
    if (!documentId) return;

    async function loadWorkspace() {
      try {
        setLoadingDocs(true);
        setLoadingConvs(true);
        const res = await fetch(`http://127.0.0.1:8000/documents/${documentId}/workspace`, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
          },
        });

        if (res.ok) {
          const data = await res.json();
          setDocuments([data.document]);
          setSelectedDocumentId(data.document.id);
          setSelectedDocumentIds(new Set([data.document.id]));
          setConversations(
            (data.conversations || []).map((c: any) => ({
              ...c,
              is_archived: c.status === 'ARCHIVED',
            }))
          );
          setCurrentConversationId(data.conversation_id);
          setMessages(
            (data.messages || []).map((m: any) => ({
              role: m.role,
              content: m.content,
              citations: m.citations,
              suggestedQuestions: m.suggestedQuestions || [],
            }))
          );
        } else {
          uiToast({
            variant: 'destructive',
            title: 'Error',
            description: 'Failed to load workspace',
          });
        }
      } catch (err) {
        console.error('Failed to load workspace:', err);
        uiToast({
          variant: 'destructive',
          title: 'Error',
          description: 'Failed to load workspace',
        });
      } finally {
        setLoadingDocs(false);
        setLoadingConvs(false);
      }
    }

    loadWorkspace();
  }, [documentId]);

  // Load messages for current conversation if switched
  useEffect(() => {
    if (!currentConversationId || !documentId) return;

    async function loadMessages() {
      try {
        const res = await fetch(
          `http://127.0.0.1:8000/documents/${documentId}/conversations/${currentConversationId}/messages`,
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
            },
          }
        );

        if (res.ok) {
          const history = await res.json();
          setMessages(
            history.map((m: any) => ({
              role: m.role,
              content: m.content,
              citations: m.citations,
              suggestedQuestions: m.suggested_questions || [],
            }))
          );
        } else {
          setMessages([
            {
              role: 'assistant',
              content: 'Ask any question about this document.',
            },
          ]);
        }
      } catch (err) {
        console.error('Failed to load messages:', err);
        setMessages([
          {
            role: 'assistant',
            content: 'Welcome to the document chat workspace.',
          },
        ]);
      }
    }

    // Skip initial fetch since workspace loads it
    if (loadingDocs || loadingConvs) return;

    loadMessages();
  }, [currentConversationId, documentId]);

  // Create new conversation
  const handleCreateConversation = async (title: string) => {
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/documents/${documentId}/conversations`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
          },
          body: JSON.stringify({ title }),
        }
      );

      if (res.ok) {
        const conv = await res.json();
        setConversations((prev) => [
          { ...conv, is_archived: conv.status === 'ARCHIVED' },
          ...prev,
        ]);
        setCurrentConversationId(conv.conversation_id);
        setMessages([]);
        toast.success('Conversation created');
      }
    } catch (err) {
      console.error('Failed to create conversation:', err);
      uiToast({
        variant: 'destructive',
        title: 'Error',
        description: 'Failed to create conversation',
      });
    }
  };

  // Rename conversation
  const handleRenameConversation = async (id: string, newTitle: string) => {
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/documents/${documentId}/conversations/${id}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
          },
          body: JSON.stringify({ title: newTitle }),
        }
      );

      if (res.ok) {
        setConversations((prev) =>
          prev.map((conv) =>
            conv.conversation_id === id ? { ...conv, title: newTitle } : conv
          )
        );
        toast.success('Conversation renamed');
      }
    } catch (err) {
      console.error('Failed to rename conversation:', err);
      uiToast({
        variant: 'destructive',
        title: 'Error',
        description: 'Failed to rename conversation',
      });
    }
  };

  // Delete conversation
  const handleDeleteConversation = async (id: string) => {
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/documents/${documentId}/conversations/${id}`,
        {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
          },
        }
      );

      if (res.ok) {
        setConversations((prev) => prev.filter((conv) => conv.conversation_id !== id));
        if (currentConversationId === id) {
          const remaining = conversations.filter((conv) => conv.conversation_id !== id);
          setCurrentConversationId(remaining[0]?.conversation_id || null);
        }
        toast.success('Conversation deleted');
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
      uiToast({
        variant: 'destructive',
        title: 'Error',
        description: 'Failed to delete conversation',
      });
    }
  };

  // Archive conversation
  const handleArchiveConversation = async (id: string) => {
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/documents/${documentId}/conversations/${id}/archive`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
          },
        }
      );

      if (res.ok) {
        setConversations((prev) =>
          prev.map((conv) =>
            conv.conversation_id === id ? { ...conv, is_archived: !conv.is_archived } : conv
          )
        );
        toast.success('Conversation archived');
      }
    } catch (err) {
      console.error('Failed to archive conversation:', err);
    }
  };

  // Pin conversation
  const handlePinConversation = async (id: string) => {
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/documents/${documentId}/conversations/${id}/pin`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
          },
        }
      );

      if (res.ok) {
        setConversations((prev) =>
          prev.map((conv) =>
            conv.conversation_id === id ? { ...conv, is_pinned: !conv.is_pinned } : conv
          )
        );
      }
    } catch (err) {
      console.error('Failed to pin conversation:', err);
      // Toggle locally as fallback if endpoint is not implemented
      setConversations((prev) =>
        prev.map((conv) =>
          conv.conversation_id === id ? { ...conv, is_pinned: !conv.is_pinned } : conv
        )
      );
    }
  };

  // Duplicate conversation
  const handleDuplicateConversation = async (id: string) => {
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/documents/${documentId}/conversations/${id}/duplicate`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
          },
        }
      );

      if (res.ok) {
        const data = await res.json();
        setConversations((prev) => [
          { ...data, is_archived: data.status === 'ARCHIVED' },
          ...prev,
        ]);
        setCurrentConversationId(data.conversation_id);
        toast.success('Conversation duplicated');
      }
    } catch (err) {
      console.error('Failed to duplicate conversation:', err);
      uiToast({
        variant: 'destructive',
        title: 'Error',
        description: 'Failed to duplicate conversation',
      });
    }
  };

  // Send message with streaming
  const handleSendMessage = async (content: string) => {
    if (!currentConversationId || !documentId || selectedDocumentIds.size === 0) {
      uiToast({
        variant: 'destructive',
        title: 'Error',
        description: 'Please select a conversation and a document',
      });
      return;
    }

    setIsStreaming(true);
    setStreamingContent('');
    setSearchStep('searching');

    // Add user message
    const userMessage: Message = { role: 'user', content };
    setMessages((prev) => [...prev, userMessage]);

    // Create abort controller
    abortControllerRef.current = new AbortController();

    try {
      setSearchStep('finding');

      const res = await fetch(
        `http://127.0.0.1:8000/documents/${documentId}/conversations/${currentConversationId}/chat`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
          },
          body: JSON.stringify({
            question: content,
            stream: true,
            mode: answerMode,
          }),
          signal: abortControllerRef.current.signal,
        }
      );

      if (!res.ok) {
        throw new Error('Failed to send message');
      }

      setSearchStep('generating');

      // Handle streaming response
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        let fullContent = '';
        let citations: any[] = [];
        let suggestedQuestions: string[] = [];

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (!line.trim()) continue;
            try {
              // Parse NDJSON lines
              const data = JSON.parse(line.startsWith('data: ') ? line.slice(6) : line);

              if (data.token) {
                fullContent += data.token;
                setStreamingContent(fullContent);
              } else if (data.stage) {
                if (data.stage === 'searching') {
                  setSearchStep('searching');
                } else if (data.stage === 'citations_found' && data.citations) {
                  citations = data.citations;
                  setSearchStep('citations');
                }
              } else if (data.question) {
                suggestedQuestions.push(data.question);
              } else if (data.error) {
                console.error('LLM stream error:', data.error);
                if (!fullContent.trim()) {
                  fullContent = data.error || "I couldn't find this information in the uploaded document.";
                }
              }
            } catch (e) {
              // Partial line chunk
            }
          }
        }

        // Add assistant message (ensure content is never an empty blank string)
        const finalContent = fullContent.trim() || "I couldn't find this information in the uploaded document.";
        const assistantMessage: Message = {
          role: 'assistant',
          content: finalContent,
          citations,
          suggestedQuestions,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        toast.info('Generation stopped');
      } else {
        console.error('Failed to send message:', err);
        uiToast({
          variant: 'destructive',
          title: 'Error',
          description: 'Failed to send message',
        });
        setMessages((prev) => [...prev, { role: 'assistant', content: 'I apologize, but I encountered an error processing your request. Please try again.' }]);
      }
    } finally {
      setIsStreaming(false);
      setStreamingContent('');
      setSearchStep('idle');
      abortControllerRef.current = null;
    }
  };

  // Stop generation
  const handleStopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  // Handle citation click
  const handleCitationClick = (citation: any) => {
    setCitationHighlight({
      document_id: citation.document_id,
      page_number: citation.page_number,
      bounding_box: citation.bounding_box,
      snippet: citation.snippet,
    });
    setSelectedDocumentId(citation.document_id);
  };

  // Handle document selection change
  const handleDocumentSelectionChange = (selectedIds: Set<string>) => {
    setSelectedDocumentIds(selectedIds);
    if (selectedIds.size === 1) {
      setSelectedDocumentId(Array.from(selectedIds)[0]);
    }
  };

  return (
    <ResponsiveLayout
      sidebar={
        <ConversationSidebar
          conversations={conversations}
          documents={documents}
          currentConversationId={currentConversationId}
          selectedDocumentIds={selectedDocumentIds}
          onConversationSelect={setCurrentConversationId}
          onNewConversation={handleCreateConversation}
          onRenameConversation={handleRenameConversation}
          onDeleteConversation={handleDeleteConversation}
          onArchiveConversation={handleArchiveConversation}
          onPinConversation={handlePinConversation}
          onDuplicateConversation={handleDuplicateConversation}
          onDocumentSelectionChange={handleDocumentSelectionChange}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          showArchived={showArchived}
          onToggleArchived={() => setShowArchived(!showArchived)}
          isLoading={loadingConvs}
        />
      }
      main={
        <ChatWindow
          messages={messages}
          isStreaming={isStreaming}
          streamingContent={streamingContent}
          searchStep={searchStep}
          answerMode={answerMode}
          onAnswerModeChange={setAnswerMode}
          onSendMessage={handleSendMessage}
          onStopGeneration={handleStopGeneration}
          onCitationClick={handleCitationClick}
          onCopyMessage={(content) => {
            navigator.clipboard.writeText(content);
            toast.success('Copied to clipboard');
          }}
          disabled={!currentConversationId}
          suggestedQuestions={messages[messages.length - 1]?.suggestedQuestions || []}
          onSuggestedQuestionClick={(question) => {
            handleSendMessage(question);
          }}
        />
      }
      rightPanel={
        <DocumentViewerPanel
          documents={documents}
          selectedDocumentId={selectedDocumentId}
          onDocumentSelect={setSelectedDocumentId}
          citationHighlight={citationHighlight}
          onHighlightClear={() => setCitationHighlight(null)}
        />
      }
    />
  );
}