import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

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

interface AnswerMode {
  value: AnswerMode;
  label: string;
  icon: React.ReactNode;
  description: string;
}

const answerModes: AnswerMode[] = [
  {
    value: 'summary',
    label: 'Summary',
    icon: <Sparkles className="h-4 w-4" />,
    description: 'Concise overview of the topic',
  },
  {
    value: 'detailed',
    label: 'Detailed',
    icon: <Sparkles className="h-4 w-4" />,
    description: 'Comprehensive explanation',
  },
  {
    value: 'explain',
    label: 'Explain',
    icon: <Sparkles className="h-4 w-4" />,
    description: 'Step-by-step explanation',
  },
  {
    value: 'compare',
    label: 'Compare',
    icon: <Sparkles className="h-4 w-4" />,
    description: 'Side-by-side comparison',
  },
  {
    value: 'timeline',
    label: 'Timeline',
    icon: <Sparkles className="h-4 w-4" />,
    description: 'Chronological sequence',
  },
  {
    value: 'bullet_points',
    label: 'Bullet Points',
    icon: <Sparkles className="h-4 w-4" />,
    description: 'Key points as bullets',
  },
  {
    value: 'flashcards',
    label: 'Flashcards',
    icon: <Sparkles className="h-4 w-4" />,
    description: 'Q&A format flashcards',
  },
  {
    value: 'key_insights',
    label: 'Key Insights',
    icon: <Sparkles className="h-4 w-4" />,
    description: 'Main takeaways',
  },
  {
    value: 'table',
    label: 'Table',
    icon: <Sparkles className="h-4 w-4" />,
    description: 'Structured table format',
  },
  {
    value: 'json',
    label: 'JSON',
    icon: <Sparkles className="h-4 w-4" />,
    description: 'Machine-readable JSON',
  },
  {
    value: 'qa',
    label: 'Q&A',
    icon: <Sparkles className="h-4 w-4" />,
    description: 'Question and answer pairs',
  },
];

interface AnswerModeSelectorProps {
  value: AnswerMode;
  onChange: (mode: AnswerMode) => void;
  disabled?: boolean;
}

export function AnswerModeSelector({ value, onChange, disabled = false }: AnswerModeSelectorProps) {
  const selectedMode = answerModes.find((mode) => mode.value === value) || answerModes[1];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          disabled={disabled}
          className="gap-2"
        >
          {selectedMode.icon}
          <span>{selectedMode.label}</span>
          <ChevronDown className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        {answerModes.map((mode) => (
          <DropdownMenuItem
            key={mode.value}
            onClick={() => onChange(mode.value)}
            className="flex flex-col items-start gap-1 p-3"
          >
            <div className="flex items-center gap-2">
              {mode.icon}
              <span className="font-medium">{mode.label}</span>
            </div>
            <span className="text-xs text-muted-foreground">{mode.description}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}