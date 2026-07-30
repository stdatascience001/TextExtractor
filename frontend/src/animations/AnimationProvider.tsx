import React from "react";
import { MotionConfig } from "framer-motion";
import { easings } from "./Timeline";

interface AnimationProviderProps {
  children: React.ReactNode;
}

export function AnimationProvider({ children }: AnimationProviderProps) {
  return (
    // reducedMotion="user" ensures all framer-motion animations respect the OS accessibility settings.
    // We can also define a central default transition here if desired, e.g., using our buttery easing curve.
    <MotionConfig 
      reducedMotion="user"
      transition={{ ease: easings.buttery }}
    >
      {children}
    </MotionConfig>
  );
}
