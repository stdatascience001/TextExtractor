import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  Search,
  MessageSquare,
  ChevronRight,
  ChevronDown,
  Trash2,
  Archive,
  RotateCcw,
  Pin,
  Folder,
  Edit2,
  Check,
  X,
  FileText,
  ArrowLeft,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip } from '@/components/ui/Tooltip';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { DocumentSelector } from './DocumentSelector';

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

interface Document {
  id: string;
  file_name: string;
  file_type: string;
  status: string;
}

interface ConversationSidebarProps {
  conversations: Conversation[];
  documents: Document[];
  currentConversationId: string | null;
  selectedDocumentIds: Set<string>;
  onConversationSelect: (id: string) => void;
  onNewConversation: (title: string) => void;
  onRenameConversation: (id: string, newTitle: string) => void;
  onDeleteConversation: (id: string) => void;
  onArchiveConversation: (id: string) => void;
  onPinConversation: (id: string) => void;
  onDuplicateConversation: (id: string) => void;
  onDocumentSelectionChange: (selectedIds: Set<string>) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  showArchived: boolean;
  onToggleArchived: () => void;
  isLoading?: boolean;
}

export function ConversationSidebar({
  conversations,
  documents,
  currentConversationId,
  selectedDocumentIds,
  onConversationSelect,
  onNewConversation,
  onRenameConversation,
  onDeleteConversation,
  onArchiveConversation,
  onPinConversation,
  onDuplicateConversation,
  onDocumentSelectionChange,
  searchQuery,
  onSearchChange,
  showArchived,
  onToggleArchived,
  isLoading = false,
}: ConversationSidebarProps) {
  const navigate = useNavigate();
  const [isRenaming, setIsRenaming] = useState<string | null>(null);
  const [renameInput, setRenameInput] = useState('');
  const [isExpanded, setIsExpanded] = useState(true);

  const filteredConversations = conversations.filter((conv) => {
    const matchesSearch = conv.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesArchive = showArchived ? conv.is_archived : !conv.is_archived;
    return matchesSearch && matchesArchive;
  });

  const pinnedConversations = filteredConversations.filter((conv) => conv.is_pinned);
  const otherConversations = filteredConversations.filter((conv) => !conv.is_pinned);

  const handleStartRename = (conv: Conversation) => {
    setIsRenaming(conv.conversation_id);
    setRenameInput(conv.title);
  };

  const handleSaveRename = () => {
    if (isRenaming && renameInput.trim()) {
      onRenameConversation(isRenaming, renameInput.trim());
    }
    setIsRenaming(null);
    setRenameInput('');
  };

  const handleCancelRename = () => {
    setIsRenaming(null);
    setRenameInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveRename();
    } else if (e.key === 'Escape') {
      handleCancelRename();
    }
  };

  return (
    <div className="flex flex-col h-full bg-card" role="complementary" aria-label="Conversations sidebar">
      {/* Header */}
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Tooltip content="Back to Document View">
            <Button
              onClick={() => navigate(documents[0] ? `/documents/${documents[0].id}` : '/my-documents')}
              variant="outline"
              size="icon"
              className="h-9 w-9 shrink-0"
              aria-label="Back to Document View"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Tooltip>
          <Tooltip content="Create New Chat" className="flex-1 w-full">
            <Button
              onClick={() => onNewConversation('New Conversation')}
              className="w-full gap-2"
              size="sm"
              aria-label="Create new conversation"
            >
              <Plus className="h-4 w-4" />
              New Chat
            </Button>
          </Tooltip>
        </div>

        <div className="mt-3 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <Input
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-9 h-9"
            aria-label="Search conversations"
            title="Search Conversations"
          />
        </div>
      </div>

      {/* Document Info */}
      <div className="p-4 border-b border-border">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">
          Active Document
        </span>
        {documents[0] ? (
          <div className="p-3 bg-muted/40 border border-border rounded-xl flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary flex-shrink-0">
              <FileText className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-foreground truncate" title={documents[0].file_name}>
                {documents[0].file_name}
              </p>
              <span className="inline-flex items-center text-[10px] font-medium text-muted-foreground uppercase mt-0.5">
                {documents[0].file_type} • {documents[0].status || 'Ready'}
              </span>
            </div>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">No document loaded</p>
        )}
      </div>

      {/* Conversations List */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-2">
          {/* Pinned Conversations */}
          {pinnedConversations.length > 0 && (
            <>
              <div className="flex items-center gap-2 px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                <Pin className="h-3 w-3" />
                Pinned
              </div>
              {pinnedConversations.map((conv) => (
                <ConversationItem
                  key={conv.conversation_id}
                  conversation={conv}
                  isActive={conv.conversation_id === currentConversationId}
                  isRenaming={isRenaming === conv.conversation_id}
                  renameInput={renameInput}
                  onRenameInputChange={setRenameInput}
                  onRenameSave={handleSaveRename}
                  onRenameCancel={handleCancelRename}
                  onRenameKeyDown={handleKeyDown}
                  onSelect={() => onConversationSelect(conv.conversation_id)}
                  onStartRename={() => handleStartRename(conv)}
                  onPin={() => onPinConversation(conv.conversation_id)}
                  onArchive={() => onArchiveConversation(conv.conversation_id)}
                  onDelete={() => onDeleteConversation(conv.conversation_id)}
                  onDuplicate={() => onDuplicateConversation(conv.conversation_id)}
                />
              ))}
              <Separator className="my-2" />
            </>
          )}

          {/* Other Conversations */}
          {otherConversations.length > 0 && (
            <>
              <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                History
              </div>
              {otherConversations.map((conv) => (
                <ConversationItem
                  key={conv.conversation_id}
                  conversation={conv}
                  isActive={conv.conversation_id === currentConversationId}
                  isRenaming={isRenaming === conv.conversation_id}
                  renameInput={renameInput}
                  onRenameInputChange={setRenameInput}
                  onRenameSave={handleSaveRename}
                  onRenameCancel={handleCancelRename}
                  onRenameKeyDown={handleKeyDown}
                  onSelect={() => onConversationSelect(conv.conversation_id)}
                  onStartRename={() => handleStartRename(conv)}
                  onPin={() => onPinConversation(conv.conversation_id)}
                  onArchive={() => onArchiveConversation(conv.conversation_id)}
                  onDelete={() => onDeleteConversation(conv.conversation_id)}
                  onDuplicate={() => onDuplicateConversation(conv.conversation_id)}
                />
              ))}
            </>
          )}

          {filteredConversations.length === 0 && !isLoading && (
            <div className="text-center py-8 text-sm text-muted-foreground">
              {searchQuery ? 'No conversations found' : 'No conversations yet'}
            </div>
          )}

          {isLoading && (
            <div className="text-center py-8 text-sm text-muted-foreground">
              Loading conversations...
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <Tooltip content={showArchived ? 'Hide Archived Conversations' : 'Show Archived Conversations'} className="w-full">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2"
            onClick={onToggleArchived}
          >
            <Folder className="h-4 w-4" />
            {showArchived ? 'Hide Archived' : 'Show Archived'}
          </Button>
        </Tooltip>
      </div>
    </div>
  );
}

interface ConversationItemProps {
  conversation: Conversation;
  isActive: boolean;
  isRenaming: boolean;
  renameInput: string;
  onRenameInputChange: (value: string) => void;
  onRenameSave: () => void;
  onRenameCancel: () => void;
  onRenameKeyDown: (e: React.KeyboardEvent) => void;
  onSelect: () => void;
  onStartRename: () => void;
  onPin: () => void;
  onArchive: () => void;
  onDelete: () => void;
  onDuplicate: () => void;
}

function ConversationItem({
  conversation,
  isActive,
  isRenaming,
  renameInput,
  onRenameInputChange,
  onRenameSave,
  onRenameCancel,
  onRenameKeyDown,
  onSelect,
  onStartRename,
  onPin,
  onArchive,
  onDelete,
  onDuplicate,
}: ConversationItemProps) {
  return (
    <div
      className={`group relative rounded-lg px-3 py-2.5 cursor-pointer transition-all ${
        isActive
          ? 'bg-primary/10 text-primary font-semibold'
          : 'text-muted-foreground hover:bg-muted/40 hover:text-foreground'
      }`}
      onClick={onSelect}
    >
      {isRenaming ? (
        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
          <Input
            value={renameInput}
            onChange={(e) => onRenameInputChange(e.target.value)}
            onKeyDown={onRenameKeyDown}
            className="h-7 text-sm"
            autoFocus
          />
          <Button size="sm" className="h-7 w-7 p-0" onClick={onRenameSave}>
            <Check className="h-3 w-3" />
          </Button>
          <Button size="sm" className="h-7 w-7 p-0" onClick={onRenameCancel}>
            <X className="h-3 w-3" />
          </Button>
        </div>
      ) : (
        <>
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                {conversation.is_pinned && (
                  <Pin className="h-3 w-3 flex-shrink-0" />
                )}
                <p className="text-sm font-medium truncate">
                  {conversation.title}
                </p>
              </div>
              {conversation.summary && (
                <p className="text-xs opacity-70 truncate mt-0.5">
                  {conversation.summary}
                </p>
              )}
            </div>
            <DropdownMenu>
              <Tooltip content="Conversation Options">
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Edit2 className="h-3 w-3" />
                  </Button>
                </DropdownMenuTrigger>
              </Tooltip>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onStartRename(); }}>
                  <Edit2 className="h-4 w-4 mr-2" />
                  Rename
                </DropdownMenuItem>
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onPin(); }}>
                  <Pin className="h-4 w-4 mr-2" />
                  {conversation.is_pinned ? 'Unpin' : 'Pin'}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onDuplicate(); }}>
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Duplicate
                </DropdownMenuItem>
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onArchive(); }}>
                  <Archive className="h-4 w-4 mr-2" />
                  Archive
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={(e) => { e.stopPropagation(); onDelete(); }}
                  className="text-destructive"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          {conversation.selected_document_ids && conversation.selected_document_ids.length > 0 && (
            <div className="flex items-center gap-1 mt-2">
              <Badge variant="secondary" className="text-xs">
                {conversation.selected_document_ids.length} doc{conversation.selected_document_ids.length > 1 ? 's' : ''}
              </Badge>
            </div>
          )}
        </>
      )}
    </div>
  );
}