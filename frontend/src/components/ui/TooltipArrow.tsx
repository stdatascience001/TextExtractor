import * as React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { cn } from "@/lib/utils";

interface TooltipArrowProps extends React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Arrow> {}

export const TooltipArrow = React.forwardRef<React.ElementRef<typeof TooltipPrimitive.Arrow>, TooltipArrowProps>(
  ({ className, ...props }, ref) => {
    
    return (
      <TooltipPrimitive.Arrow
        ref={ref}
        className={cn("fill-background/90 w-3 h-1.5 opacity-90", className)}
        {...props}
      />
    );
  }
);
TooltipArrow.displayName = "TooltipArrow";
