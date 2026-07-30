import * as React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { motion, AnimatePresence } from "framer-motion";
import { TooltipCard } from "./TooltipCard";
import { TooltipArrow } from "./TooltipArrow";
import { cn } from "@/lib/utils";

export interface TooltipProps extends Omit<TooltipPrimitive.TooltipProps, "delayDuration"> {
  content?: React.ReactNode;
  title?: React.ReactNode;
  description?: React.ReactNode;
  icon?: React.ReactNode;
  shortcut?: string;
  status?: string;
  placement?: TooltipPrimitive.TooltipContentProps["side"];
  align?: TooltipPrimitive.TooltipContentProps["align"];
  className?: string;
  cardClassName?: string;
  interactive?: boolean;
  maxWidth?: number;
  delay?: number;
  disabled?: boolean;
}

export function Tooltip({
  children,
  content,
  title,
  description,
  icon,
  shortcut,
  status,
  placement = "top",
  align = "center",
  className,
  cardClassName,
  interactive = false,
  open: controlledOpen,
  onOpenChange,
  defaultOpen,
  delay = 120,
  maxWidth,
  disabled = false,
}: TooltipProps) {
  const [internalOpen, setInternalOpen] = React.useState(defaultOpen || false);
  
  const isControlled = controlledOpen !== undefined;
  const open = disabled ? false : (isControlled ? controlledOpen : internalOpen);
  
  const handleOpenChange = (newOpen: boolean) => {
    if (disabled) return;
    if (!isControlled) {
      setInternalOpen(newOpen);
    }
    onOpenChange?.(newOpen);
  };

  // Spring physics for entrance
  const springConfig = { type: "spring" as const, stiffness: 400, damping: 25, mass: 1 };
  
  return (
    <TooltipPrimitive.Root
      open={open}
      onOpenChange={handleOpenChange}
      delayDuration={delay}
      defaultOpen={defaultOpen}
    >
      <TooltipPrimitive.Trigger asChild>
        <motion.div
          className={cn("inline-flex items-center justify-center cursor-default", className)}
          whileHover={{ y: -1 }} // Micro-interaction: Lift 1px on hover
          whileTap={{ scale: 0.97 }} // Micro-interaction: Tap feedback
        >
          {children}
        </motion.div>
      </TooltipPrimitive.Trigger>

      <AnimatePresence>
        {open && (
          <TooltipPrimitive.Portal forceMount>
            <TooltipPrimitive.Content
              side={placement}
              align={align}
              sideOffset={8}
              asChild
              style={{ pointerEvents: interactive ? "auto" : "none" }}
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.94, y: placement === "top" ? 8 : placement === "bottom" ? -8 : placement === "left" ? 8 : -8, filter: "blur(8px)" }}
                animate={{ opacity: 1, scale: 1, y: 0, filter: "blur(0px)" }}
                exit={{ opacity: 0, scale: 0.96, filter: "blur(4px)", transition: { duration: 0.15, ease: "easeOut" } }}
                transition={springConfig}
                className="z-50"
              >
                <TooltipCard
                  title={title}
                  description={description || content}
                  icon={icon}
                  shortcut={shortcut}
                  status={status}
                  maxWidth={maxWidth}
                  className={cardClassName}
                />
                <TooltipArrow />
              </motion.div>
            </TooltipPrimitive.Content>
          </TooltipPrimitive.Portal>
        )}
      </AnimatePresence>
    </TooltipPrimitive.Root>
  );
}
