import React from "react";
import { MotionConfig } from "framer-motion";

interface AnimationProviderProps {
  children: React.ReactNode;
}

/**
 * Global Animation Provider
 * 
 * - Configures framer-motion defaults for the entire application.
 * - Ensures strict compliance with OS-level `prefers-reduced-motion` settings.
 * - When `reducedMotion="user"` is active, Framer Motion will intelligently 
 *   disable layout shifts, transforms, and scaling, while falling back to 
 *   simple opacity fades so the UI remains accessible and usable.
 */
export function AnimationProvider({ children }: AnimationProviderProps) {
  return (
    <MotionConfig reducedMotion="user">
      {children}
    </MotionConfig>
  );
}
