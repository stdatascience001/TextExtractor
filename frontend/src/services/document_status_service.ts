import { api } from "../lib/api";
import { DocumentLifecycle } from "../lib/DocumentLifecycle";

interface PollingInstance {
  documentId: string;
  onUpdate: (status: string) => void;
  onError?: (err: any) => void;
  startTime: number;
  intervalId: any;
  abortController: AbortController | null;
  lastStatus: string | null;
}

class DocumentStatusServiceClass {
  private activePolls = new Map<string, PollingInstance>();
  private isTabVisible = true;

  constructor() {
    if (typeof window !== "undefined" && typeof document !== "undefined") {
      document.addEventListener("visibilitychange", this.handleVisibilityChange.bind(this));
    }
  }

  private handleVisibilityChange() {
    this.isTabVisible = document.visibilityState === "visible";
    console.log(`DocumentStatusService: Tab visibility changed. Visible: ${this.isTabVisible}`);
    
    if (this.isTabVisible) {
      // Resume all active polls
      for (const [docId, instance] of this.activePolls.entries()) {
        this.restartInterval(instance);
      }
    } else {
      // Pause all active intervals (but keep instances in tracking)
      for (const [docId, instance] of this.activePolls.entries()) {
        this.clearActiveInterval(instance);
      }
    }
  }

  public startPolling(
    documentId: string,
    onUpdate: (status: string) => void,
    onError?: (err: any) => void
  ) {
    // If already polling, just update callbacks to prevent duplicates
    if (this.activePolls.has(documentId)) {
      const existing = this.activePolls.get(documentId)!;
      existing.onUpdate = onUpdate;
      existing.onError = onError;
      return;
    }

    const instance: PollingInstance = {
      documentId,
      onUpdate,
      onError,
      startTime: Date.now(),
      intervalId: null,
      abortController: null,
      lastStatus: null
    };

    this.activePolls.set(documentId, instance);
    
    // Execute first immediate fetch
    this.pollStep(instance);
    
    if (this.isTabVisible) {
      this.restartInterval(instance);
    }
  }

  public stopPolling(documentId: string) {
    const instance = this.activePolls.get(documentId);
    if (instance) {
      this.clearActiveInterval(instance);
      if (instance.abortController) {
        instance.abortController.abort();
      }
      this.activePolls.delete(documentId);
      console.log(`DocumentStatusService: Stopped polling for document ${documentId}`);
    }
  }

  private getAdaptiveInterval(elapsedSeconds: number): number {
    if (elapsedSeconds < 20) {
      return 2000; // First 20s: poll every 2s
    } else if (elapsedSeconds < 60) {
      return 5000; // Next 40s: poll every 5s
    } else {
      return 10000; // Thereafter: poll every 10s
    }
  }

  private clearActiveInterval(instance: PollingInstance) {
    if (instance.intervalId) {
      clearInterval(instance.intervalId);
      instance.intervalId = null;
    }
  }

  private restartInterval(instance: PollingInstance) {
    this.clearActiveInterval(instance);
    
    const elapsedSeconds = (Date.now() - instance.startTime) / 1000;
    const intervalTime = this.getAdaptiveInterval(elapsedSeconds);

    instance.intervalId = setInterval(() => {
      this.pollStep(instance);
      
      // Adapt interval dynamically if threshold is crossed
      const currentElapsed = (Date.now() - instance.startTime) / 1000;
      const nextInterval = this.getAdaptiveInterval(currentElapsed);
      if (nextInterval !== intervalTime) {
        this.restartInterval(instance);
      }
    }, intervalTime);
  }

  private async pollStep(instance: PollingInstance) {
    if (!this.isTabVisible) return;

    if (instance.abortController) {
      instance.abortController.abort();
    }
    instance.abortController = new AbortController();

    try {
      // Direct call to lightweight status endpoint
      const res = await fetch(`http://127.0.0.1:8000/documents/${instance.documentId}/status`, {
        signal: instance.abortController.signal,
        headers: localStorage.getItem("accessToken") 
          ? { Authorization: `Bearer ${localStorage.getItem("accessToken")}` } 
          : {}
      });

      if (!res.ok) {
        throw new Error(`HTTP status error: ${res.status}`);
      }

      const data = await res.json();
      const newStatus = data.status;

      if (newStatus !== instance.lastStatus) {
        instance.lastStatus = newStatus;
        instance.onUpdate(newStatus);
      }

      // Check if terminal state reached
      if (DocumentLifecycle.isTerminal(newStatus)) {
        console.log(`DocumentStatusService: Terminal state reached (${newStatus}) for ${instance.documentId}. Halting polling.`);
        this.stopPolling(instance.documentId);
      }
    } catch (err: any) {
      if (err.name === "AbortError") return; // ignore expected aborts
      console.error(`DocumentStatusService: Poll error for ${instance.documentId}:`, err);
      if (instance.onError) {
        instance.onError(err);
      }
    }
  }
}

export const DocumentStatusService = new DocumentStatusServiceClass();
