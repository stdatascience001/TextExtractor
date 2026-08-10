export const RUNNING_STATES = [
  "uploaded",
  "parsing",
  "ready_for_chunking",
  "ready_for_embedding",
  "ready_for_validation",
  "ocr_running",
  "chunking_running",
  "embedding_running",
  "extraction_running",
  "conflict_running",
  "clarification_running"
];

export const TERMINAL_STATES = [
  "ready_for_chat",
  "ready_for_reindex",
  "failed",
  "cancelled",
  "completed"
];

export const READY_STATES = [
  "ready_for_chat",
  "completed"
];

export const FAILED_STATES = [
  "failed"
];

export const CANCELLED_STATES = [
  "cancelled"
];

export const DocumentLifecycle = {
  isRunning: (status?: string): boolean => {
    if (!status) return false;
    const lower = status.toLowerCase();
    return RUNNING_STATES.includes(lower) && !TERMINAL_STATES.includes(lower);
  },

  isTerminal: (status?: string): boolean => {
    if (!status) return false;
    return TERMINAL_STATES.includes(status.toLowerCase());
  },

  isReady: (status?: string): boolean => {
    if (!status) return false;
    return READY_STATES.includes(status.toLowerCase());
  },

  isFailed: (status?: string): boolean => {
    if (!status) return false;
    return FAILED_STATES.includes(status.toLowerCase());
  },

  isCancelled: (status?: string): boolean => {
    if (!status) return false;
    return CANCELLED_STATES.includes(status.toLowerCase());
  }
};

export interface IngestionStageConfig {
  key: string;
  label: string;
  statusKeyword: string;
  progressPercent: number;
  desc: string;
}

export const INGESTION_STAGES: IngestionStageConfig[] = [
  { key: "uploaded", label: "Queued", statusKeyword: "uploaded", progressPercent: 5, desc: "Awaiting workspace thread capacity" },
  { key: "parsing", label: "OCR & Document Parsing", statusKeyword: "ocr", progressPercent: 20, desc: "Extracting raw and handwritten text" },
  { key: "chunking", label: "Semantic Segment Chunking", statusKeyword: "chunking", progressPercent: 40, desc: "Layout-aware semantic chunk formatting" },
  { key: "embedding", label: "Vector Ingestion", statusKeyword: "embedding", progressPercent: 60, desc: "Generating and saving chunk embeddings" },
  { key: "validation", label: "Pipeline Validation", statusKeyword: "validation", progressPercent: 80, desc: "Verifying document consistency and reports" },
  { key: "ready_for_chat", label: "Completed", statusKeyword: "ready_for_chat", progressPercent: 100, desc: "Ingestion successfully completed" }
];
