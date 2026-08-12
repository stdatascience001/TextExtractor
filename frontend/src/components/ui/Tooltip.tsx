import React, { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface TooltipProps {
  content: React.ReactNode;
  description?: React.ReactNode;
  children: React.ReactElement;
  position?: "top" | "bottom" | "left" | "right";
  className?: string;
}

export function Tooltip({ content, description, children, position = "top", className }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const triggerRef = useRef<HTMLElement>(null);
  const [coords, setCoords] = useState({ top: 0, left: 0 });

  const updateCoords = () => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const scrollX = window.scrollX;
    const scrollY = window.scrollY;

    const triggerCenterX = rect.left + rect.width / 2;
    const triggerCenterY = rect.top + rect.height / 2;

    let top = 0;
    let left = 0;

    // Standard positions with 6px gap
    if (position === "top") {
      top = rect.top - 6 + scrollY;
      left = triggerCenterX + scrollX;
    } else if (position === "bottom") {
      top = rect.bottom + 6 + scrollY;
      left = triggerCenterX + scrollX;
    } else if (position === "left") {
      top = triggerCenterY + scrollY;
      left = rect.left - 6 + scrollX;
    } else if (position === "right") {
      top = triggerCenterY + scrollY;
      left = rect.right + 6 + scrollX;
    }

    // Viewport constraints (ensure left/right boundary clipping protection)
    const padding = 12;
    const viewportWidth = window.innerWidth;

    // Estimate width limits (assume a safe center constraint)
    if (left < padding) left = padding;
    if (left > viewportWidth - padding) left = viewportWidth - padding;

    setCoords({ top, left });
  };

  useEffect(() => {
    if (visible) {
      updateCoords();
      window.addEventListener("resize", updateCoords, { passive: true });
      window.addEventListener("scroll", updateCoords, { passive: true });
    }
    return () => {
      window.removeEventListener("resize", updateCoords);
      window.removeEventListener("scroll", updateCoords);
    };
  }, [visible]);

  // Position transform styles
  const translateStyles = {
    top: "translate(-50%, -100%)",
    bottom: "translate(-50%, 0)",
    left: "translate(-100%, -50%)",
    right: "translate(0, -50%)",
  };

  const child = React.Children.only(children);
  const trigger = React.cloneElement(child, {
    ref: triggerRef,
    onMouseEnter: (e: any) => {
      child.props.onMouseEnter?.(e);
      setVisible(true);
    },
    onMouseLeave: (e: any) => {
      child.props.onMouseLeave?.(e);
      setVisible(false);
    },
    onFocus: (e: any) => {
      child.props.onFocus?.(e);
      setVisible(true);
    },
    onBlur: (e: any) => {
      child.props.onBlur?.(e);
      setVisible(false);
    },
  });

  return (
    <>
      {trigger}
      {typeof document !== "undefined" &&
        createPortal(
          <AnimatePresence>
            {visible && (
              <motion.div
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.96 }}
                transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
                style={{
                  position: "absolute",
                  top: coords.top,
                  left: coords.left,
                  transform: translateStyles[position],
                  pointerEvents: "none",
                  zIndex: 9999,
                }}
                className={cn(
                  // Frosted translucent glass background
                  "bg-white/95 dark:bg-zinc-950/95 backdrop-blur-md",
                  // Realistic double-border / inner light reflection highlight
                  "border border-zinc-200/80 dark:border-zinc-800/80",
                  "before:absolute before:inset-0 before:rounded-lg before:border before:border-white/10 dark:before:border-white/5 before:pointer-events-none",
                  // Soft depth shadow
                  "shadow-[0_4px_12px_-2px_rgba(0,0,0,0.06),0_0_1px_rgba(0,0,0,0.12)]",
                  // Dynamic padding and flex layout based on content depth
                  "rounded-lg pointer-events-none text-left z-[9999] w-max max-w-[220px]",
                  description
                    ? "p-2.5 flex flex-col gap-0.5"
                    : "px-2 py-1 whitespace-nowrap text-[11px] font-medium tracking-tight text-zinc-900 dark:text-zinc-50",
                  className
                )}
              >
                {description ? (
                  <>
                    <div className="text-[11px] font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
                      {content}
                    </div>
                    <hr />
                    <div className="text-[9.5px] font-medium leading-tight text-zinc-500 dark:text-zinc-400">
                      {description}
                    </div>
                  </>
                ) : (
                  content
                )}
              </motion.div>
            )}
          </AnimatePresence>,
          document.body
        )}
    </>
  );
}
