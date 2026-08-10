import React from 'react';
import { motion } from 'framer-motion';
import { Copy, ThumbsUp, ThumbsDown, MoreVertical, Bookmark, Share2, RotateCcw, BotMessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
  onCopy?: () => void;
  onRegenerate?: () => void;
  onLike?: () => void;
  onDislike?: () => void;
  onBookmark?: () => void;
  children?: React.ReactNode;
}

export function MessageBubble({
  role,
  content,
  isStreaming = false,
  onCopy,
  onRegenerate,
  onLike,
  onDislike,
  onBookmark,
  children,
}: MessageBubbleProps) {
  const { user } = useAuth();

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      toast.success('Copied to clipboard');
      onCopy?.();
    } catch (err) {
      toast.error('Failed to copy');
    }
  };

  const getUserInitials = () => {
    if (user?.username) {
      return user.username.substring(0, 2).toUpperCase();
    }
    if (user?.email) {
      return user.email.substring(0, 2).toUpperCase();
    }
    return 'US';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`group flex gap-3 ${role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
      role="article"
      aria-label={`${role} message`}
    >
      {/* Avatar */}
      <div 
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          role === 'user' 
            ? 'bg-primary text-primary-foreground text-xs font-semibold' 
            : 'bg-primary/10 text-primary'
        }`}
        aria-hidden="true"
      >
        {role === 'user' ? (
          <span>{getUserInitials()}</span>
        ) : (
          <BotMessageSquare className="h-4 w-4" />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 max-w-3xl ${role === 'user' ? 'flex flex-col items-end' : ''}`}>
        <div className={`rounded-2xl px-4 py-3 ${
          role === 'user'
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted/50 border border-border'
        }`}>
          {children || (
            <div className={`prose prose-sm max-w-none ${
              role === 'user' ? 'prose-invert' : 'prose-gray'
            }`}>
              {content}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        {!isStreaming && (
          <div 
            className={`flex items-center gap-1 mt-1 opacity-0 group-hover:opacity-100 transition-opacity ${
              role === 'user' ? 'justify-end' : 'justify-start'
            }`}
            role="toolbar"
            aria-label={`Message actions for ${role}`}
          >
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={handleCopy}
              aria-label="Copy message"
            >
              <Copy className="h-3.5 w-3.5" />
            </Button>

            {role === 'assistant' && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={onLike}
                  aria-label="Like message"
                >
                  <ThumbsUp className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={onDislike}
                  aria-label="Dislike message"
                >
                  <ThumbsDown className="h-3.5 w-3.5" />
                </Button>
                {onRegenerate && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={onRegenerate}
                    aria-label="Regenerate response"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                  </Button>
                )}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0"
                      aria-label="More options"
                    >
                      <MoreVertical className="h-3.5 w-3.5" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={onBookmark}>
                      <Bookmark className="h-4 w-4 mr-2" />
                      Bookmark
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                      <Share2 className="h-4 w-4 mr-2" />
                      Share
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}