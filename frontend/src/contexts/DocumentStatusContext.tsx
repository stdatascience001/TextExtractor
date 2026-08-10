import React, { createContext, useContext, useMemo } from "react";
import { useDocumentStatus as useHookStatus } from "../hooks/useDocumentStatus";

interface DocumentStatusContextType {
  status: string | null;
  error: any;
  isRunning: boolean;
  isReady: boolean;
  isFailed: boolean;
  isTerminal: boolean;
}

const DocumentStatusContext = createContext<DocumentStatusContextType | null>(null);

export const DocumentStatusProvider: React.FC<{
  documentId?: string;
  children: React.ReactNode;
}> = ({ documentId, children }) => {
  const statusState = useHookStatus(documentId);

  const memoizedValue = useMemo(() => statusState, [
    statusState.status,
    statusState.error,
    statusState.isRunning,
    statusState.isReady,
    statusState.isFailed,
    statusState.isTerminal
  ]);

  return (
    <DocumentStatusContext.Provider value={memoizedValue}>
      {children}
    </DocumentStatusContext.Provider>
  );
};

export const useDocumentStatusContext = () => {
  const context = useContext(DocumentStatusContext);
  if (!context) {
    throw new Error("useDocumentStatusContext must be used within a DocumentStatusProvider");
  }
  return context;
};
