import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';

interface StreamingMessageProps {
  content: string;
  isComplete: boolean;
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
  onCitationClick?: (citation: any) => void;
}

export function StreamingMessage({
  content,
  isComplete,
  citations = [],
  onCitationClick,
}: StreamingMessageProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [content]);

  const MarkdownComponents = {
    code({ node, inline, className, children, ...props }: any) {
      const match = /language-(\w+)/.exec(className || '');
      return !inline && match ? (
        <SyntaxHighlighter
          style={vscDarkPlus}
          language={match[1]}
          PreTag="div"
          className="rounded-lg"
          {...props}
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      ) : (
        <code className="bg-muted px-1.5 py-0.5 rounded text-sm" {...props}>
          {children}
        </code>
      );
    },
    p({ children }: any) {
      return <p className="mb-2 last:mb-0">{children}</p>;
    },
    ul({ children }: any) {
      return <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>;
    },
    ol({ children }: any) {
      return <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>;
    },
    li({ children }: any) {
      return <li>{children}</li>;
    },
    h1({ children }: any) {
      return <h1 className="text-xl font-bold mb-2">{children}</h1>;
    },
    h2({ children }: any) {
      return <h2 className="text-lg font-semibold mb-2">{children}</h2>;
    },
    h3({ children }: any) {
      return <h3 className="text-base font-semibold mb-2">{children}</h3>;
    },
    blockquote({ children }: any) {
      return (
        <blockquote className="border-l-4 border-primary pl-4 italic my-2">
          {children}
        </blockquote>
      );
    },
    table({ children }: any) {
      return (
        <div className="overflow-x-auto my-2">
          <table className="min-w-full border border-border rounded-lg">
            {children}
          </table>
        </div>
      );
    },
    thead({ children }: any) {
      return <thead className="bg-muted">{children}</thead>;
    },
    tbody({ children }: any) {
      return <tbody>{children}</tbody>;
    },
    tr({ children }: any) {
      return <tr className="border-b border-border">{children}</tr>;
    },
    th({ children }: any) {
      return <th className="px-4 py-2 text-left font-semibold">{children}</th>;
    },
    td({ children }: any) {
      return <td className="px-4 py-2">{children}</td>;
    },
  };

  return (
    <MessageBubble role="assistant" content={content} isStreaming={!isComplete}>
      <div className="prose prose-sm max-w-none prose-gray">
        {!isComplete && content === '' ? (
          <TypingIndicator />
        ) : (
          <ReactMarkdown components={MarkdownComponents}>
            {content}
          </ReactMarkdown>
        )}
      </div>
      <div ref={messagesEndRef} />
    </MessageBubble>
  );
}