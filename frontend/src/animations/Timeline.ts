import { Transition } from "framer-motion";

// Cinematic Easing Curves (Linear, Stripe, Apple inspired)
export const easings = {
  easeOutExpo: [0.19, 1, 0.22, 1],
  easeInOutExpo: [0.87, 0, 0.13, 1],
  easeOutCirc: [0.075, 0.82, 0.165, 1],
  easeOutQuart: [0.25, 1, 0.5, 1],
  easeOutQuint: [0.23, 1, 0.32, 1],
  // Custom buttery smooth curve
  buttery: [0.22, 1, 0.36, 1],
};

// Reusable Spring Presets
export const springs: Record<"fast" | "medium" | "slow" | "dramatic", Transition> = {
  fast: { type: "spring", stiffness: 500, damping: 30, mass: 1 },
  medium: { type: "spring", stiffness: 300, damping: 25, mass: 1 },
  slow: { type: "spring", stiffness: 150, damping: 20, mass: 1 },
  dramatic: { type: "spring", stiffness: 100, damping: 15, mass: 1.5 },
};

// Global Timeline Configurations
export const timelines = {
  microInteraction: 0.15,
  base: 0.3,
  slow: 0.5,
  cinematic: 1.2,
};
