import * as React from "react";
import { cn } from "@/lib/utils";

export interface TooltipCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: React.ReactNode;
  description?: React.ReactNode;
  icon?: React.ReactNode;
  shortcut?: string;
  status?: string;
  maxWidth?: number;
}

export const TooltipCard = React.forwardRef<HTMLDivElement, TooltipCardProps>(
  ({ className, title, description, icon, shortcut, status, maxWidth = 280, children, ...props }, ref) => {
    
    return (
      <div
        ref={ref}
        className={cn(
          "flex flex-col gap-1.5 rounded-xl border p-3 backdrop-blur-2xl transition-colors text-sm shadow-[0_8px_30px_rgb(0,0,0,0.12)] bg-background/90 text-foreground border-border/50",
          className
        )}
        style={{ maxWidth }}
        {...props}
      >
        {/* Header (Icon + Title + Status) */}
        {(icon || title || status) && (
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              {icon && <span className="flex items-center justify-center shrink-0">{icon}</span>}
              {title && <span className="font-semibold tracking-tight">{title}</span>}
            </div>
            {status && (
              <span className="text-[10px] uppercase font-bold tracking-wider opacity-70 bg-black/20 px-1.5 py-0.5 rounded">
                {status}
              </span>
            )}
          </div>
        )}

        {/* Divider if title + desc exist */}
        {(title || icon) && (description || children) && (
          <div className="h-px w-full bg-current opacity-10 my-0.5" />
        )}

        {/* Body (Description + Children) */}
        {(description || children) && (
          <div className="text-current/90 text-xs leading-relaxed">
            {description}
            {children}
          </div>
        )}

        {/* Footer (Shortcut) */}
        {shortcut && (
          <div className="mt-1 flex items-center justify-end">
            <kbd className="inline-flex h-5 items-center gap-1 rounded border border-current/20 bg-current/10 px-1.5 text-[10px] font-medium opacity-80 shadow-sm">
              {shortcut}
            </kbd>
          </div>
        )}
      </div>
    );
  }
);
TooltipCard.displayName = "TooltipCard";
