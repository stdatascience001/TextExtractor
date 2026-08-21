import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { motion, AnimatePresence, type Variants } from "framer-motion";
import {
  UploadCloud,
  Cpu,
  FolderPlus,
  MessageSquare,
  Sparkles,
  ShieldCheck,
  ChevronRight,
  ChevronLeft,
  CheckCircle2,
} from "lucide-react";

interface HowItWorksModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface GuideItem {
  id: string;
  stepNumber: number;
  stepBadge: string;
  tabTitle: string;
  tabSubtitle: string;
  mainHeading: string;
  instructions: {
    label: string;
    detail: string;
  }[];
  icon: React.ReactNode;
  watermarkIcon: React.ReactNode;
}

const stepsData: GuideItem[] = [
  {
    id: "step-upload",
    stepNumber: 1,
    stepBadge: "Step 01 • Document Ingestion",
    tabTitle: "1. Upload File",
    tabSubtitle: "PDF, Image or Sheet",
    mainHeading: "Upload your document or paste a public Google Sheet link to start.",
    instructions: [
      {
        label: "Drag & Drop Files",
        detail: "Upload PDF, JPG, PNG, DOCX, TXT, CSV, or Excel files into the dropzone box.",
      },
      {
        label: "Google Sheet Link",
        detail: "Or paste any public Google Spreadsheet URL and click 'Import'.",
      },
      {
        label: "Auto Trigger",
        detail: "The pipeline automatically processes OCR and text parsing upon upload.",
      },
    ],
    icon: <UploadCloud className="h-5 w-5 text-primary" />,
    watermarkIcon: <UploadCloud className="h-56 w-56 text-primary/10 dark:text-primary/15" />,
  },
  {
    id: "step-ai-ocr",
    stepNumber: 2,
    stepBadge: "Step 02 • Intelligent Extraction",
    tabTitle: "2. AI OCR Engine",
    tabSubtitle: "Split-Screen & Search",
    mainHeading: "View interactive split-screen document and extracted text side-by-side.",
    instructions: [
      {
        label: "Split-Screen View",
        detail: "Review high-resolution original pages on the left and raw extracted text on the right.",
      },
      {
        label: "Keyword Search",
        detail: "Search words or phrases with live occurrence counters and matched text highlighting.",
      },
      {
        label: "Copy & Export",
        detail: "Copy entire document text or individual page extracts with a single click.",
      },
    ],
    icon: <Cpu className="h-5 w-5 text-primary" />,
    watermarkIcon: <Cpu className="h-56 w-56 text-primary/10 dark:text-primary/15" />,
  },
  {
    id: "step-project-manage",
    stepNumber: 3,
    stepBadge: "Step 03 • Project Hub",
    tabTitle: "3. Organize & Save",
    tabSubtitle: "Context & Versioning",
    mainHeading: "Assign extractions to active projects for persistent tracking.",
    instructions: [
      {
        label: "Active Project Context",
        detail: "Select or switch projects from the sidebar header badge or project selector.",
      },
      {
        label: "Save Extractions",
        detail: "Click 'Save Document' to archive OCR results directly to your project.",
      },
      {
        label: "Export Formats",
        detail: "Download parsed documents as structured JSON, CSV, or formatted text.",
      },
    ],
    icon: <FolderPlus className="h-5 w-5 text-primary" />,
    watermarkIcon: <FolderPlus className="h-56 w-56 text-primary/10 dark:text-primary/15" />,
  },
  {
    id: "step-ask-ai",
    stepNumber: 4,
    stepBadge: "Step 04 • AI Knowledge Chat",
    tabTitle: "4. Ask AI",
    tabSubtitle: "Query Your Documents",
    mainHeading: "Converse with your documents using contextual AI analysis.",
    instructions: [
      {
        label: "Semantic Q&A",
        detail: "Chat with individual files in Document View or across all files in Knowledge View.",
      },
      {
        label: "Source Attribution",
        detail: "AI responses cite specific page numbers and document fragments for verification.",
      },
      {
        label: "Instant Insights",
        detail: "Ask questions like 'Summarize key points', 'Extract totals', or 'Find specific clauses'.",
      },
    ],
    icon: <MessageSquare className="h-5 w-5 text-primary" />,
    watermarkIcon: <MessageSquare className="h-56 w-56 text-primary/10 dark:text-primary/15" />,
  },
];

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.05,
    },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] as const },
  },
};

export const HowItWorksModal: React.FC<HowItWorksModalProps> = ({
  open,
  onOpenChange,
}) => {
  const [activeIndex, setActiveIndex] = useState<number>(0);

  const handleNext = () => {
    setActiveIndex((prev) => (prev < stepsData.length - 1 ? prev + 1 : prev));
  };

  const handlePrev = () => {
    setActiveIndex((prev) => (prev > 0 ? prev - 1 : prev));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl sm:max-w-4xl bg-card border-border/80 shadow-2xl p-0 overflow-hidden rounded-2xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="relative bg-gradient-to-br from-primary/10 via-primary/5 to-transparent p-6 pb-4 border-b border-border/60"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 mb-1">
              <motion.span
                whileHover={{ rotate: 15 }}
                className="p-1.5 rounded-lg bg-primary/10 text-primary cursor-default"
              >
                <Sparkles className="h-4 w-4" />
              </motion.span>
              <span className="text-xs font-semibold text-primary uppercase tracking-wider">
                User Guide
              </span>
            </div>
            {/* Step Pill Counter */}
            <motion.span
              key={activeIndex}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="text-xs font-medium px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20"
            >
              Step {activeIndex + 1} of {stepsData.length}
            </motion.span>
          </div>
          <DialogTitle className="text-xl sm:text-2xl font-bold text-foreground tracking-tight">
            How to Extract Documents & Chat with AI
          </DialogTitle>
          <DialogDescription className="text-xs sm:text-sm text-muted-foreground mt-0.5">
            Follow these 4 simple steps to extract data from any file and start conversing with AI.
          </DialogDescription>
        </motion.div>

        {/* Modal Body: Interactive Showcase Accordion */}
        <div className="p-5 sm:p-6 space-y-4">
          {/* Desktop Expanding Accordion */}
          <div className="hidden sm:flex h-[360px] gap-2.5 w-full">
            {stepsData.map((item, idx) => {
              const isActive = activeIndex === idx;

              return (
                <motion.button
                  key={item.id}
                  type="button"
                  layout
                  onClick={() => setActiveIndex(idx)}
                  whileHover={{ scale: isActive ? 1 : 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  className="group relative basis-0 overflow-hidden rounded-xl bg-card border border-border/60 text-left transition-[flex-grow] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] shadow-sm hover:border-border cursor-pointer select-none"
                  style={{ flexGrow: isActive ? 12 : 1 }}
                >
                  {/* Background Radial Gradient */}
                  <div className="pointer-events-none absolute inset-0 rounded-xl bg-[radial-gradient(120%_100%_at_50%_0%,rgba(255,255,255,0.7)_0%,rgba(255,255,255,0)_60%),linear-gradient(180deg,rgba(255,255,255,0.5)_0%,rgba(0,0,0,0.02)_100%)] dark:bg-[radial-gradient(120%_100%_at_50%_0%,rgba(255,255,255,0.06)_0%,rgba(255,255,255,0)_60%),linear-gradient(180deg,rgba(255,255,255,0.02)_0%,rgba(0,0,0,0.15)_100%)] opacity-90 transition-opacity duration-300" />

                  <AnimatePresence mode="wait">
                    {isActive ? (
                      /* Active Expanded Step */
                      <motion.div
                        key={`modal-active-${item.id}`}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.25 }}
                        className="relative z-10 flex h-full w-full flex-col justify-between p-6"
                      >
                        {/* Watermark Icon */}
                        <div className="pointer-events-none absolute right-2 bottom-2 overflow-hidden">
                          <motion.div
                            initial={{ scale: 0.8, opacity: 0 }}
                            animate={{ scale: 1, opacity: 0.2 }}
                            transition={{ duration: 0.4 }}
                          >
                            {item.watermarkIcon}
                          </motion.div>
                        </div>

                        {/* Top Header */}
                        <motion.div
                          initial={{ opacity: 0, y: -6 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.3 }}
                          className="relative z-10"
                        >
                          <span className="inline-block text-[11px] font-bold text-primary mb-1 uppercase tracking-wider">
                            {item.stepBadge}
                          </span>
                          <h3 className="text-base sm:text-lg font-semibold text-foreground leading-snug tracking-tight">
                            {item.mainHeading}
                          </h3>
                        </motion.div>

                        {/* Middle Step Instructions List */}
                        <motion.div
                          variants={containerVariants}
                          initial="hidden"
                          animate="visible"
                          className="relative z-10 grid grid-cols-1 md:grid-cols-3 gap-2.5 my-2"
                        >
                          {item.instructions.map((inst, i) => (
                            <motion.div
                              key={i}
                              variants={itemVariants}
                              whileHover={{ y: -2 }}
                              className="p-3 rounded-lg bg-muted/50 dark:bg-muted/30 border border-border/60 flex flex-col justify-start transition-shadow hover:shadow-sm"
                            >
                              <div className="flex items-center gap-1.5 mb-1">
                                <CheckCircle2 className="h-3.5 w-3.5 text-primary shrink-0" />
                                <span className="text-xs font-semibold text-foreground">
                                  {inst.label}
                                </span>
                              </div>
                              <p className="text-[11px] text-muted-foreground leading-relaxed">
                                {inst.detail}
                              </p>
                            </motion.div>
                          ))}
                        </motion.div>

                        {/* Bottom Bar: Action / Icon & Next/Prev */}
                        <motion.div
                          initial={{ opacity: 0, y: 6 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.3, delay: 0.1 }}
                          className="relative z-10 flex w-full items-center justify-between pt-2 border-t border-border/40"
                        >
                          <div className="flex items-center gap-2.5">
                            <motion.div
                              whileHover={{ rotate: 10, scale: 1.05 }}
                              className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0"
                            >
                              {item.icon}
                            </motion.div>
                            <div>
                              <p className="text-xs font-semibold text-foreground leading-tight">
                                {item.tabTitle}
                              </p>
                              <p className="text-[10px] text-muted-foreground leading-tight">
                                {item.tabSubtitle}
                              </p>
                            </div>
                          </div>

                          {/* Navigation controls inside accordion */}
                          <div className="flex items-center gap-1.5">
                            {idx > 0 && (
                              <motion.button
                                type="button"
                                whileHover={{ scale: 1.04 }}
                                whileTap={{ scale: 0.96 }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handlePrev();
                                }}
                                className="px-2.5 py-1 text-xs font-medium rounded-md border border-border hover:bg-muted text-muted-foreground hover:text-foreground flex items-center gap-1 cursor-pointer transition-colors"
                              >
                                <ChevronLeft className="h-3.5 w-3.5" /> Previous
                              </motion.button>
                            )}
                            {idx < stepsData.length - 1 ? (
                              <motion.button
                                type="button"
                                whileHover={{ scale: 1.04 }}
                                whileTap={{ scale: 0.96 }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleNext();
                                }}
                                className="px-2.5 py-1 text-xs font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 flex items-center gap-1 cursor-pointer transition-colors"
                              >
                                Next Step <ChevronRight className="h-3.5 w-3.5" />
                              </motion.button>
                            ) : (
                              <motion.button
                                type="button"
                                whileHover={{ scale: 1.04 }}
                                whileTap={{ scale: 0.96 }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onOpenChange(false);
                                }}
                                className="px-3 py-1 text-xs font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 flex items-center gap-1 cursor-pointer transition-colors shadow-sm"
                              >
                                Start Now ✨
                              </motion.button>
                            )}
                          </div>
                        </motion.div>
                      </motion.div>
                    ) : (
                      /* Collapsed Tab */
                      <motion.div
                        key={`modal-inactive-${item.id}`}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="relative z-10 flex h-full w-full flex-col items-center justify-between p-3.5"
                      >
                        <div className="[writing-mode:vertical-rl] [text-orientation:mixed] flex flex-col items-center text-left pt-2">
                          <span className="text-xs font-semibold text-foreground tracking-tight opacity-85 group-hover:opacity-100 group-hover:text-primary transition-all">
                            {item.tabTitle}
                          </span>
                        </div>

                        <div className="h-7 w-7 rounded-lg bg-muted/60 flex items-center justify-center opacity-70 group-hover:opacity-100 group-hover:bg-primary/10 group-hover:text-primary transition-all">
                          {item.icon}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.button>
              );
            })}
          </div>

          {/* Mobile Accordion */}
          <div className="flex flex-col gap-2.5 sm:hidden w-full">
            {stepsData.map((item, idx) => {
              const isActive = activeIndex === idx;

              return (
                <motion.button
                  key={`modal-mob-${item.id}`}
                  type="button"
                  layout
                  onClick={() => setActiveIndex(idx)}
                  whileTap={{ scale: 0.98 }}
                  className={`group relative w-full overflow-hidden rounded-xl bg-card border border-border/60 text-left shadow-sm cursor-pointer ${
                    isActive ? "p-4" : "h-[54px] px-3.5 flex items-center"
                  }`}
                >
                  <div className="pointer-events-none absolute inset-0 rounded-xl bg-[radial-gradient(120%_100%_at_50%_0%,rgba(255,255,255,0.7)_0%,rgba(255,255,255,0)_60%),linear-gradient(180deg,rgba(255,255,255,0.4)_0%,rgba(0,0,0,0.02)_100%)] dark:bg-[radial-gradient(120%_100%_at_50%_0%,rgba(255,255,255,0.06)_0%,rgba(255,255,255,0)_60%),linear-gradient(180deg,rgba(255,255,255,0.02)_0%,rgba(0,0,0,0.15)_100%)] opacity-90" />

                  <AnimatePresence mode="wait">
                    {isActive ? (
                      <motion.div
                        key={`mob-active-item-${item.id}`}
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.3 }}
                        className="relative z-10 flex h-full flex-col gap-3"
                      >
                        <div>
                          <span className="text-[10px] font-bold text-primary uppercase tracking-wider">
                            {item.stepBadge}
                          </span>
                          <h4 className="text-sm font-semibold text-foreground mt-0.5">
                            {item.mainHeading}
                          </h4>
                        </div>

                        <div className="space-y-2">
                          {item.instructions.map((inst, i) => (
                            <div key={i} className="p-2 rounded-lg bg-muted/40 border border-border/60">
                              <p className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                                <CheckCircle2 className="h-3 w-3 text-primary shrink-0" />
                                {inst.label}
                              </p>
                              <p className="text-[11px] text-muted-foreground mt-0.5">
                                {inst.detail}
                              </p>
                            </div>
                          ))}
                        </div>

                        <div className="flex items-center justify-between pt-2 border-t border-border/40">
                          <div className="flex items-center gap-2">
                            <div className="h-6 w-6 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                              {item.icon}
                            </div>
                            <span className="text-xs font-medium text-foreground">
                              {item.tabTitle}
                            </span>
                          </div>
                          {idx < stepsData.length - 1 ? (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleNext();
                              }}
                              className="px-2.5 py-1 text-xs bg-primary text-primary-foreground rounded-md"
                            >
                              Next
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                onOpenChange(false);
                              }}
                              className="px-2.5 py-1 text-xs bg-primary text-primary-foreground rounded-md"
                            >
                              Done
                            </button>
                          )}
                        </div>
                      </motion.div>
                    ) : (
                      <motion.div
                        key={`mob-inactive-item-${item.id}`}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="relative z-10 flex w-full items-center justify-between"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-primary">
                            0{item.stepNumber}
                          </span>
                          <span className="text-xs font-semibold text-foreground">
                            {item.tabTitle}
                          </span>
                        </div>
                        <div className="h-6 w-6 flex items-center justify-center opacity-70 group-hover:text-primary transition-colors">
                          {item.icon}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.button>
              );
            })}
          </div>

          {/* Pro Tips Footer Box */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.15 }}
            className="p-3.5 rounded-xl bg-primary/5 border border-primary/20 flex items-start gap-3"
          >
            <ShieldCheck className="h-5 w-5 text-primary shrink-0 mt-0.5" />
            <div className="space-y-0.5 text-xs">
              <p className="font-semibold text-foreground">
                Quick Navigation Tips
              </p>
              <p className="text-muted-foreground leading-normal">
                Want to chat across all uploaded files? Click <strong>Knowledge</strong> on the left sidebar to start multi-document AI discussions. For single document extraction, manage your files directly from <strong>Documents</strong>.
              </p>
            </div>
          </motion.div>
        </div>

        {/* Footer Bar */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="p-3.5 px-6 bg-muted/30 border-t border-border/60 flex items-center justify-between"
        >
          <span className="text-xs text-muted-foreground hidden sm:inline">
            Click any tab above or use Next / Previous buttons to navigate.
          </span>
          <motion.button
            type="button"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => onOpenChange(false)}
            className="w-full sm:w-auto px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-medium rounded-lg transition-colors cursor-pointer text-center ml-auto shadow-sm"
          >
            Close Guide
          </motion.button>
        </motion.div>
      </DialogContent>
    </Dialog>
  );
};
