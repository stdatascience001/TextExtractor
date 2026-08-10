import { useState, useEffect } from "react";
import { DocumentStatusService } from "../services/document_status_service";
import { DocumentLifecycle } from "../lib/DocumentLifecycle";

export function useDocumentStatus(documentId?: string) {
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<any>(null);

  useEffect(() => {
    if (!documentId) return;

    // Start polling status
    DocumentStatusService.startPolling(
      documentId,
      (newStatus) => {
        setStatus(newStatus);
        setError(null);
      },
      (err) => {
        setError(err);
      }
    );

    return () => {
      DocumentStatusService.stopPolling(documentId);
    };
  }, [documentId]);

  return {
    status,
    error,
    isRunning: DocumentLifecycle.isRunning(status || undefined),
    isReady: DocumentLifecycle.isReady(status || undefined),
    isFailed: DocumentLifecycle.isFailed(status || undefined),
    isTerminal: DocumentLifecycle.isTerminal(status || undefined)
  };
}
