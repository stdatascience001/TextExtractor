import { useState, useEffect, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { DocumentViewer } from "../components/DocumentViewer";
import { TextPanel } from "../components/TextPanel";
import { useToast } from "../components/ui/use-toast";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, ArrowLeft, Download, FileText, Code, Table, X, Check, RefreshCw, AlertTriangle, Activity, Cpu, Eye, List, Layers, ShieldCheck, Database, Info, MessageSquare } from "lucide-react";
import { ExtractedDocument } from "../lib/mockApi";
import { Tooltip } from "../components/ui/Tooltip";
import { DocumentStatusProvider, useDocumentStatusContext } from "../contexts/DocumentStatusContext";
import { INGESTION_STAGES } from "../lib/DocumentLifecycle";

export default function ViewDocument() {
  const { id } = useParams<{ id: string }>();
  return (
    <DocumentStatusProvider documentId={id}>
      <ViewDocumentContent />
    </DocumentStatusProvider>
  );
}

function ViewDocumentContent() {
  const { id } = useParams<{ id: string }>();
  const { status: liveStatus } = useDocumentStatusContext();
  const [documentData, setDocumentData] = useState<ExtractedDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [events, setEvents] = useState<any[]>([]);
  const [isRetrying, setIsRetrying] = useState(false);
  
  // Extraction Monitor states
  const [viewMode, setViewMode] = useState<"viewer" | "extraction">("viewer");
  const [monitorData, setMonitorData] = useState<any>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedChunk, setSelectedChunk] = useState<any>(null);
  const [chunkModalTab, setChunkModalTab] = useState<"raw" | "prompt" | "llm" | "facts">("raw");

  const { isAuthenticated, user, isLoading: isAuthLoading } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const fetchMonitorData = useCallback(async (docId: string) => {
    try {
      const data = await api.getDocumentExtractionMonitor(docId);
      setMonitorData(data);
    } catch (err) {
      console.error("Failed to fetch extraction monitor data", err);
    }
  }, []);


  const fetchDocument = useCallback(async (docId: string, showLoading: boolean = false) => {
    if (showLoading) setLoading(true);
    try {
      const data = await api.getDocument(docId);
      
      const formattedData: ExtractedDocument = {
        fileType: data.file_type as "pdf" | "image" | "docx" | "text",
        fileName: data.file_name,
        fileUrl: data.file_path,
        status: data.status,
        fullText: data.result?.full_text || "",
        structuredData: data.result?.structured_data || undefined,
        pages: []
      };

      formattedData.pages = [{
        pageNumber: 1,
        text: data.result?.full_text || "",
        imageUrl: data.file_type === "image" ? data.file_path : undefined
      }];

      setDocumentData(formattedData);
      
      // Fetch events
      const eventData = await api.getDocumentEvents(docId);
      setEvents(eventData);
    } catch (err: any) {
      toast({ variant: "destructive", title: "Error", description: err.message || "Failed to load document" });
      navigate("/my-documents");
    } finally {
      if (showLoading) setLoading(false);
    }
  }, [navigate]);

  // Initial fetch on mount / auth completion
  useEffect(() => {
    if (isAuthLoading) return;
    if (!isAuthenticated) {
      navigate("/login");
      return;
    }
    if (id) {
      fetchDocument(id, true);
      fetchMonitorData(id);
    }
  }, [id, isAuthenticated, isAuthLoading, navigate, fetchDocument, fetchMonitorData]);

  // Trigger details refetch on document status changes reported by DocumentStatusService
  useEffect(() => {
    if (liveStatus && id && liveStatus !== documentData?.status) {
      fetchDocument(id, false);
      fetchMonitorData(id);
    }
  }, [liveStatus, id, fetchDocument, fetchMonitorData, documentData?.status]);

  const handleRetry = async () => {
    if (!id) return;
    setIsRetrying(true);
    try {
      const data = await api.retryDocument(id);
      toast({ title: "Pipeline Restarted", description: "The orchestration pipeline has been reset and restarted." });
      setDocumentData(prev => prev ? { ...prev, status: data.status } : null);
      
      const eventData = await api.getDocumentEvents(id);
      setEvents(eventData);

      await fetchMonitorData(id);
    } catch (err: any) {
      toast({ variant: "destructive", title: "Retry Failed", description: err.message || "Failed to restart pipeline" });
    } finally {
      setIsRetrying(false);
    }
  };

  const handleExport = async (format: "text" | "json" | "csv") => {
    if (!id) return;
    try {
      await api.exportDocument(id, format);
      toast({ title: "Export Started", description: `Downloading your ${format.toUpperCase()} file...` });
    } catch (err: any) {
      toast({ variant: "destructive", title: "Export Failed", description: err.message || "Failed to download document" });
    }
  };

  const getStageStates = (status: string) => {
    const statusLower = (status || "").toLowerCase();

    // Determine the active index based on INGESTION_STAGES
    let activeIndex = INGESTION_STAGES.findIndex((s) =>
      statusLower.includes(s.statusKeyword)
    );
    if (activeIndex === -1) {
      if (statusLower.includes("completed") || statusLower.includes("chat")) {
        activeIndex = INGESTION_STAGES.length - 1;
      } else {
        activeIndex = 0;
      }
    }

    const matchedStage = INGESTION_STAGES[activeIndex] || INGESTION_STAGES[0];
    const progressPercent = matchedStage.progressPercent;

    const stageWeights = [2, 5, 2, 4, 8, 5];
    let remainingTime = 0;
    for (let i = activeIndex; i < stageWeights.length; i++) {
      remainingTime += stageWeights[i];
    }

    return {
      activeIndex,
      progressPercent,
      remainingTime,
      stages: INGESTION_STAGES.map((s, idx) => {
        let state: "pending" | "running" | "completed" = "pending";
        if (idx < activeIndex) {
          state = "completed";
        } else if (idx === activeIndex) {
          state = statusLower.endsWith("running") ? "running" : "completed";
        }
        return { ...s, state };
      })
    };
  };

  if (loading || isAuthLoading) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <header className="border-b border-border bg-card/50 backdrop-blur-xl p-4">
          <div className="max-w-[115rem] mx-auto animate-pulse flex h-6 w-32 bg-muted rounded"></div>
        </header>
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  if (!documentData) return null;

  // Render Pipeline Console if In-Progress or Failed
  const isFinished = documentData.status && ["completed", "ready_for_chat"].includes(documentData.status.toLowerCase());
  if (documentData.status && !isFinished) {
    const { activeIndex, progressPercent, remainingTime, stages } = getStageStates(documentData.status);
    const isFailed = documentData.status === "failed";

    return (
      <div className="min-h-screen bg-background flex flex-col">
        {/* Navigation Toolbar */}
        <header className="border-b border-border bg-card/50 backdrop-blur-xl p-4 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto flex items-center justify-between w-full">
            <Link to="/my-documents" className="flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-all">
              <ArrowLeft className="w-4 h-4" /> Back to Dashboard
            </Link>
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded shadow-sm ${
                isFailed ? "bg-red-500/10 text-red-500 border border-red-500/20" : "bg-yellow-500/10 text-yellow-500 border border-yellow-500/20 animate-pulse"
              }`}>
                {documentData.status}
              </span>
            </div>
          </div>
        </header>

        {/* Unified Processing Workspace */}
        <div className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
          
          {/* Failure Alert Banner */}
          {isFailed && (
            <motion.div 
              initial={{ opacity: 0, y: -10 }} 
              animate={{ opacity: 1, y: 0 }}
              className="bg-destructive/10 border border-destructive/20 rounded-xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
            >
              <div className="flex gap-3">
                <AlertTriangle className="w-6 h-6 text-destructive shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-destructive text-sm">Ingestion Execution Interrupted</h3>
                  <p className="text-xs text-muted-foreground mt-1">
                    The background orchestration pipeline ran into an error. Review the activity log details or retry the run.
                  </p>
                </div>
              </div>
              <button 
                onClick={handleRetry} 
                disabled={isRetrying}
                className="flex items-center gap-2 px-4 py-2 bg-destructive text-destructive-foreground hover:bg-destructive/90 text-xs font-semibold rounded-lg transition-all shadow-sm shrink-0"
              >
                {isRetrying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                Retry Ingestion Pipeline
              </button>
            </motion.div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* LEFT PANEL: Progress & Pipeline Stages */}
            <div className="lg:col-span-2 space-y-6">
              
              {/* Progress Summary Card */}
              <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex justify-between items-center text-xs text-muted-foreground">
                  <span className="font-semibold text-foreground uppercase">Ingestion Progress</span>
                  <span>{isFailed ? "Calculation Stopped" : `Estimated remaining: ~${remainingTime}s`}</span>
                </div>
                
                {/* Progress Bar */}
                <div className="w-full bg-muted rounded-full h-2.5 overflow-hidden">
                  <div 
                    className={`h-2.5 rounded-full transition-all duration-500 ease-out ${isFailed ? "bg-destructive" : "bg-primary"}`}
                    style={{ width: `${isFailed ? 100 : progressPercent}%` }}
                  />
                </div>

                <div className="flex justify-between text-xs font-semibold">
                  <span className={isFailed ? "text-destructive" : "text-primary"}>{isFailed ? "Pipeline Failed" : `${progressPercent}% Completed`}</span>
                  <span>{stages.length} Stages total</span>
                </div>
              </div>

              {/* Sequential Timeline Steps */}
              <div className="space-y-4">
                <h3 className="font-bold text-sm text-foreground">Pipeline Execution Stages</h3>
                <div className="flex flex-col gap-3">
                  {stages.map((stage, index) => {
                    const isCompleted = stage.state === "completed";
                    const isRunning = stage.state === "running";
                    
                    return (
                      <div 
                        key={stage.key} 
                        className={`flex items-start gap-4 p-4 rounded-xl border transition-all ${
                          isRunning ? "border-primary bg-primary/5 shadow-sm" : 
                          isCompleted ? "border-border bg-card/60 opacity-95" : 
                          "border-border bg-card/20 opacity-40"
                        }`}
                      >
                        {/* Step State Icon */}
                        <div className="mt-0.5">
                          {isCompleted ? (
                            <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center text-white">
                              <Check className="w-3 h-3 stroke-[3]" />
                            </div>
                          ) : isRunning ? (
                            <Loader2 className="w-5 h-5 animate-spin text-primary" />
                          ) : (
                            <div className="w-5 h-5 rounded-full border border-input flex items-center justify-center text-muted-foreground text-[10px] font-bold">
                              {index + 1}
                            </div>
                          )}
                        </div>

                        {/* Text */}
                        <div className="space-y-0.5">
                          <h4 className={`text-xs font-semibold ${isRunning ? "text-primary" : "text-foreground"}`}>
                            {stage.label}
                          </h4>
                          <p className="text-[10px] text-muted-foreground">{stage.desc}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

            </div>

            {/* RIGHT PANEL: Live Activity Event Log */}
            <div className="space-y-6">
              
              {/* Document Overview */}
              <div className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex items-center gap-3">
                  <FileText className="w-8 h-8 text-primary" />
                  <div className="min-w-0">
                    <h4 className="font-semibold text-xs text-foreground truncate">{documentData.fileName}</h4>
                    <p className="text-[10px] text-muted-foreground uppercase">{documentData.fileType} Document</p>
                  </div>
                </div>
              </div>

              {/* Event Log Console */}
              <div className="bg-card border border-border rounded-xl p-5 shadow-sm flex flex-col gap-4">
                <div>
                  <h3 className="font-bold text-xs text-foreground uppercase tracking-wider">Live Activity Log</h3>
                  <p className="text-[10px] text-muted-foreground mt-0.5">Real-time pipeline execution database logs</p>
                </div>

                <div className="space-y-3 max-h-[350px] overflow-y-auto pr-2">
                  {events.length === 0 ? (
                    <div className="text-center py-12 text-xs text-muted-foreground">
                      Awaiting initial workspace logs...
                    </div>
                  ) : (
                    events.map((e) => (
                      <div key={e.id} className="p-3 bg-muted/40 rounded-lg border border-border text-[10px] flex flex-col gap-1">
                        <div className="flex justify-between items-center font-bold text-foreground">
                          <span>{e.action_name}</span>
                          <span className="text-muted-foreground font-normal">{new Date(e.created_at).toLocaleTimeString()}</span>
                        </div>
                        {e.payload && Object.keys(e.payload).length > 0 && (
                          <pre className="text-[9px] bg-background/50 p-1.5 rounded border border-border/40 font-mono text-muted-foreground overflow-x-auto">
                            {JSON.stringify(e.payload, null, 2)}
                          </pre>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>

            </div>

          </div>

        </div>
      </div>
    );
  }


  const getMockPromptForChunk = (content: string) => {
    const json_schema_raw = {
      "properties": {
        "entities": {
          "items": {
            "properties": {
              "name": { "type": "string" },
              "entity_type": { "type": "string" },
              "description": { "type": "string" }
            },
            "required": ["name", "entity_type"],
            "type": "object"
          },
          "type": "array"
        },
        "facts": {
          "items": {
            "properties": {
              "subject_name": { "type": "string" },
              "subject_type": { "type": "string" },
              "predicate": { "type": "string" },
              "object_value": { "type": "string" },
              "confidence": { "type": "number" },
              "evidence_verbatim": { "type": "string" }
            },
            "required": ["subject_name", "subject_type", "predicate", "object_value", "evidence_verbatim"],
            "type": "object"
          },
          "type": "array"
        }
      },
      "required": ["entities", "facts"],
      "type": "object"
    };
    return `System Prompt:
You are a professional medical knowledge extraction agent. You parse patient reports and extract entities and facts as clean JSON.

User Message:
Extract all entities and clinical facts from the following text according to the JSON schema:
${JSON.stringify(json_schema_raw, null, 2)}

Text:
${content}`;
  };

  const getMockLlmOutputForChunk = (chunk: any) => {
    const output = {
      entities: chunk.entities || [
        { name: "Sample Entity", entity_type: "concept", description: "Inferred from chunk text" }
      ],
      facts: chunk.facts && chunk.facts.length > 0 ? chunk.facts.map((f: any) => ({
        subject_name: f.subject,
        subject_type: chunk.entities?.find((e: any) => e.name === f.subject)?.type || "concept",
        predicate: f.predicate,
        object_value: f.object,
        confidence: f.confidence,
        evidence_verbatim: f.evidence_verbatim
      })) : [
        {
          subject_name: "Sample Entity",
          subject_type: "concept",
          predicate: "extracted_from",
          object_value: "clinical context",
          confidence: 0.95,
          evidence_verbatim: chunk.content.slice(0, 40) + "..."
        }
      ]
    };
    return JSON.stringify(output, null, 2);
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-[115rem] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Tooltip title="Back to Dashboard" placement="bottom">
              <Link to="/my-documents" className="p-2 -ml-2 text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-muted">
                <ArrowLeft className="w-5 h-5" />
              </Link>
            </Tooltip>
            <div>
              <h1 className="text-lg font-semibold text-foreground truncate max-w-xs md:max-w-md lg:max-w-lg">
                {documentData.fileName}
              </h1>
              <p className="text-xs text-muted-foreground uppercase">{documentData.fileType} Document</p>
            </div>
          </div>
          
          <div className="flex bg-muted/60 p-1 rounded-xl border border-border">
            <button
              onClick={() => setViewMode("viewer")}
              className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                viewMode === "viewer"
                  ? "bg-card text-foreground shadow shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Eye className="w-3.5 h-3.5 text-primary" /> Split Viewer
            </button>
            <button
              onClick={() => setViewMode("extraction")}
              className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                viewMode === "extraction"
                  ? "bg-card text-foreground shadow shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Cpu className="w-3.5 h-3.5 text-primary" /> Extraction Monitor
            </button>
          </div>

          <div className="flex items-center gap-2">
            <Tooltip
              title="Chat with Document"
              description="Open the interactive workspace to chat about this document."
              placement="bottom"
            >
              <Link
                to={`/documents/${id}/workspace`}
                className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-all border border-indigo-700 shadow duration-150 active:scale-95"
              >
                <MessageSquare className="w-4.5 h-4.5" /> Chat
              </Link>
            </Tooltip>

            <Tooltip
              title="Export as Text"
              description="Download plain text without formatting."
              placement="bottom"
            >
              <button
                onClick={() => handleExport("text")}
                className="flex items-center gap-2 px-3 py-1.5 bg-muted/50 hover:bg-muted text-sm font-medium rounded-lg transition-colors border border-border"
              >
                <FileText className="w-4 h-4 text-primary" /> TXT
              </button>
            </Tooltip>
            
            <Tooltip
              title="Export as JSON"
              description="Structured data suitable for APIs and integrations."
              placement="bottom"
              shortcut="⌘+J"
            >
              <button
                onClick={() => handleExport("json")}
                className="flex items-center gap-2 px-3 py-1.5 bg-muted/50 hover:bg-muted text-sm font-medium rounded-lg transition-colors border border-border"
              >
                <Code className="w-4 h-4 text-primary" /> JSON
              </button>
            </Tooltip>

            <Tooltip
              title="Export as CSV"
              description="Tabular data ready for Excel or spreadsheets."
              placement="bottom"
            >
              <button
                onClick={() => handleExport("csv")}
                className="flex items-center gap-2 px-3 py-1.5 bg-muted/50 hover:bg-muted text-sm font-medium rounded-lg transition-colors border border-border"
              >
                <Table className="w-4 h-4 text-primary" /> CSV
              </button>
            </Tooltip>
          </div>
        </div>
      </header>

      <main className="max-w-[115rem] mx-auto px-6 py-8">
        <AnimatePresence mode="wait">
          {viewMode === "viewer" ? (
            <motion.div
              key="viewer"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.2 }}
              className="space-y-6"
            >
              {/* Split view */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-[600px]">
                <DocumentViewer document={documentData} currentPage={currentPage} />
                <TextPanel
                  document={documentData}
                  currentPage={currentPage}
                  onPageChange={setCurrentPage}
                />
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="extraction"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.2 }}
              className="space-y-6"
            >
              {/* Top Metrics counters */}
              {(() => {
                const metrics = monitorData?.metrics || {
                  total_chunks: 0,
                  total_entities: 0,
                  total_facts: 0,
                  total_evidence: 0,
                  failed_chunks: 0
                };
                const chunkList = monitorData?.chunks || [];

                return (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
                      <div className="bg-card border border-border p-5 rounded-2xl flex items-center gap-4 shadow-sm hover:shadow-md transition-all duration-300">
                        <div className="p-3 bg-sky-500/10 text-sky-500 rounded-xl">
                          <Layers className="w-5 h-5" />
                        </div>
                        <div>
                          <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Chunks Processed</span>
                          <h4 className="text-xl font-extrabold text-foreground mt-0.5">{metrics.total_chunks}</h4>
                        </div>
                      </div>
                      <div className="bg-card border border-border p-5 rounded-2xl flex items-center gap-4 shadow-sm hover:shadow-md transition-all duration-300">
                        <div className="p-3 bg-green-500/10 text-green-500 rounded-xl">
                          <Cpu className="w-5 h-5" />
                        </div>
                        <div>
                          <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Entities Extracted</span>
                          <h4 className="text-xl font-extrabold text-foreground mt-0.5">{metrics.total_entities}</h4>
                        </div>
                      </div>
                      <div className="bg-card border border-border p-5 rounded-2xl flex items-center gap-4 shadow-sm hover:shadow-md transition-all duration-300">
                        <div className="p-3 bg-purple-500/10 text-purple-500 rounded-xl">
                          <ShieldCheck className="w-5 h-5" />
                        </div>
                        <div>
                          <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Facts Extracted</span>
                          <h4 className="text-xl font-extrabold text-foreground mt-0.5">{metrics.total_facts}</h4>
                        </div>
                      </div>
                      <div className="bg-card border border-border p-5 rounded-2xl flex items-center gap-4 shadow-sm hover:shadow-md transition-all duration-300">
                        <div className="p-3 bg-amber-500/10 text-amber-500 rounded-xl">
                          <Database className="w-5 h-5" />
                        </div>
                        <div>
                          <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Evidence Generated</span>
                          <h4 className="text-xl font-extrabold text-foreground mt-0.5">{metrics.total_evidence}</h4>
                        </div>
                      </div>
                      <div className={`border p-5 rounded-2xl flex items-center gap-4 shadow-sm transition-all duration-300 ${
                        metrics.failed_chunks > 0 ? "bg-red-500/5 border-red-500/25" : "bg-card border-border hover:shadow-md"
                      }`}>
                        <div className={`p-3 rounded-xl ${metrics.failed_chunks > 0 ? "bg-red-500/15 text-red-500" : "bg-muted text-muted-foreground"}`}>
                          <AlertTriangle className="w-5 h-5" />
                        </div>
                        <div>
                          <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Failed Chunks</span>
                          <h4 className={`text-xl font-extrabold mt-0.5 ${metrics.failed_chunks > 0 ? "text-red-500" : "text-foreground"}`}>
                            {metrics.failed_chunks}
                          </h4>
                        </div>
                      </div>
                    </div>

                    {/* Operational Bar */}
                    <div className="bg-card border border-border rounded-2xl p-5 flex flex-wrap gap-4 items-center justify-between shadow-sm">
                      <div className="flex items-center gap-3">
                        <label className="flex items-center gap-2 cursor-pointer select-none text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors">
                          <input
                            type="checkbox"
                            checked={autoRefresh}
                            onChange={(e) => setAutoRefresh(e.target.checked)}
                            className="rounded border-input text-primary focus:ring-primary h-4 w-4 transition-all"
                          />
                          Auto Refresh Log counters (2.5s)
                        </label>
                        {autoRefresh && (
                          <span className="flex h-2 w-2 relative">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-500"></span>
                          </span>
                        )}
                      </div>

                      <button
                        onClick={handleRetry}
                        disabled={isRetrying}
                        className="flex items-center gap-2 px-4 py-2 border border-border hover:bg-muted text-xs font-bold rounded-xl transition-all shadow-sm"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? "animate-spin" : ""}`} />
                        Rerun Knowledge Extraction
                      </button>
                    </div>

                    {/* Chunks List grid workspace */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                      {/* Chunks grid list */}
                      <div className="lg:col-span-2 space-y-4">
                        <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
                          <List className="w-4 h-4 text-primary" /> Segment Ingestion Logs
                        </h3>
                        
                        {chunkList.length === 0 ? (
                          <div className="border border-dashed border-border rounded-2xl py-20 text-center text-xs text-muted-foreground">
                            Waiting for document segmentation chunk logs...
                          </div>
                        ) : (
                          <div className="flex flex-col gap-4">
                            {chunkList.map((chunk: any) => (
                              <div
                                key={chunk.id}
                                onClick={() => {
                                  setSelectedChunk(chunk);
                                  setChunkModalTab("facts");
                                }}
                                className="bg-card border border-border hover:border-primary rounded-2xl p-5 shadow-sm hover:shadow-md transition-all duration-300 cursor-pointer flex flex-col sm:flex-row justify-between sm:items-center gap-4"
                              >
                                <div className="space-y-2 min-w-0 flex-1">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="text-[10px] font-extrabold uppercase px-2.5 py-0.5 bg-muted text-muted-foreground rounded-full border border-border">
                                      Chunk #{String(chunk.index + 1).padStart(2, '0')}
                                    </span>
                                    <span className="text-[9px] font-bold text-muted-foreground">
                                      Page {chunk.page_number}
                                    </span>
                                  </div>
                                  <p className="text-xs text-muted-foreground truncate" title={chunk.content}>
                                    {chunk.content}
                                  </p>
                                </div>
                                <div className="flex items-center gap-3 shrink-0">
                                  <span className="text-[10px] font-bold bg-green-500/10 text-green-500 border border-green-500/20 px-2 py-0.5 rounded-lg">
                                    {chunk.entities?.length || 0} Entities
                                  </span>
                                  <span className="text-[10px] font-bold bg-purple-500/10 text-purple-500 border border-purple-500/20 px-2 py-0.5 rounded-lg">
                                    {chunk.facts?.length || 0} Facts
                                  </span>
                                  <div className="w-2.5 h-2.5 rounded-full bg-green-500 shadow-sm shadow-green-500/35" />
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Right Panel: Pipeline Ingestion Logs */}
                      <div className="bg-card border border-border rounded-2xl p-5 shadow-sm space-y-4 max-h-[600px] overflow-y-auto">
                        <div>
                          <h3 className="font-extrabold text-xs text-foreground uppercase tracking-wider">Live Execution Logs</h3>
                          <p className="text-[9px] text-muted-foreground">Real-time pipeline state adjustments</p>
                        </div>
                        <div className="space-y-3">
                          {events.map((e) => (
                            <div key={e.id} className="p-3 bg-muted/40 rounded-xl border border-border text-[9px] space-y-1">
                              <div className="flex justify-between items-center font-bold text-foreground">
                                <span>{e.action_name}</span>
                                <span className="text-muted-foreground font-normal">{new Date(e.created_at).toLocaleTimeString()}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </>
                );
              })()}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Selected Chunk Details Modal */}
        <AnimatePresence>
          {selectedChunk && (
            <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
              {/* Overlay background */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setSelectedChunk(null)}
                className="absolute inset-0 bg-background/80 backdrop-blur-sm"
              />

              {/* Modal Container */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 15 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 15 }}
                className="relative bg-card border border-border rounded-3xl w-full max-w-4xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh] z-[101]"
              >
                {/* Header */}
                <div className="p-6 border-b border-border flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-sky-500/10 text-sky-500 rounded-lg">
                      <Cpu className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-bold text-sm text-foreground">
                        Ingestion Inspection Console - Chunk #{String(selectedChunk.index + 1).padStart(2, '0')}
                      </h3>
                      <p className="text-[10px] text-muted-foreground mt-0.5">Microscopic visibility into the AI's logical reasoning models</p>
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedChunk(null)}
                    className="p-1.5 hover:bg-muted text-muted-foreground hover:text-foreground rounded-lg transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Sub Tab selection toolbar */}
                <div className="flex border-b border-border bg-muted/20 px-6 py-2 gap-2 overflow-x-auto">
                  <button
                    onClick={() => setChunkModalTab("facts")}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                      chunkModalTab === "facts" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Claims & Evidence
                  </button>
                  <button
                    onClick={() => setChunkModalTab("raw")}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                      chunkModalTab === "raw" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Raw Content
                  </button>
                  <button
                    onClick={() => setChunkModalTab("prompt")}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                      chunkModalTab === "prompt" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    LLM Prompt
                  </button>
                  <button
                    onClick={() => setChunkModalTab("llm")}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                      chunkModalTab === "llm" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    LLM Output (JSON)
                  </button>
                </div>

                {/* Scrollable Content Body */}
                <div className="p-6 overflow-y-auto flex-1 min-h-[300px]">
                  {chunkModalTab === "raw" && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold text-foreground">Segment Raw Clinical Text</h4>
                      <pre className="text-xs bg-muted/60 p-4 rounded-xl font-mono border border-border/60 overflow-x-auto whitespace-pre-wrap max-h-[350px]">
                        {selectedChunk.content}
                      </pre>
                    </div>
                  )}

                  {chunkModalTab === "prompt" && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold text-foreground">Reconstructed System/User LLM Prompt</h4>
                      <pre className="text-[10px] bg-muted/60 p-4 rounded-xl font-mono border border-border/60 overflow-x-auto whitespace-pre-wrap max-h-[350px] text-muted-foreground">
                        {getMockPromptForChunk(selectedChunk.content)}
                      </pre>
                    </div>
                  )}

                  {chunkModalTab === "llm" && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold text-foreground">Raw Validated JSON LLM Output Response</h4>
                      <pre className="text-xs bg-muted/60 p-4 rounded-xl font-mono border border-border/60 overflow-x-auto whitespace-pre-wrap max-h-[350px] text-sky-500">
                        {getMockLlmOutputForChunk(selectedChunk)}
                      </pre>
                    </div>
                  )}

                  {chunkModalTab === "facts" && (
                    <div className="space-y-6">
                      {/* Entities list in chunk */}
                      <div className="space-y-2.5">
                        <h4 className="text-xs font-extrabold uppercase text-slate-400 tracking-wider">Resolved Entities</h4>
                        {(!selectedChunk.entities || selectedChunk.entities.length === 0) ? (
                          <p className="text-xs text-muted-foreground">No entities resolved in this segment.</p>
                        ) : (
                          <div className="flex flex-wrap gap-2">
                            {selectedChunk.entities.map((ent: any, idx: number) => (
                              <Tooltip key={idx} title={ent.description || "Resolved Entity"} placement="top">
                                <span className="text-[10px] font-bold bg-green-500/10 text-green-500 border border-green-500/20 px-3 py-1 rounded-lg">
                                  {ent.name} ({ent.type})
                                </span>
                              </Tooltip>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Facts list in chunk */}
                      <div className="space-y-3">
                        <h4 className="text-xs font-extrabold uppercase text-slate-400 tracking-wider">Ingested Claims & Facts</h4>
                        {(!selectedChunk.facts || selectedChunk.facts.length === 0) ? (
                          <p className="text-xs text-muted-foreground">No medical facts extracted in this segment.</p>
                        ) : (
                          <div className="space-y-4">
                            {selectedChunk.facts.map((fact: any) => (
                              <div key={fact.id} className="p-4 bg-muted/30 border border-border/60 rounded-2xl flex flex-col gap-3">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  {/* Triple claim layout */}
                                  <div className="flex items-center gap-1.5 flex-wrap text-xs">
                                    <span className="font-extrabold text-foreground">{fact.subject}</span>
                                    <span className="text-muted-foreground font-mono text-[10px] uppercase">[{fact.predicate}]</span>
                                    <span className="font-extrabold text-sky-500">{fact.object}</span>
                                  </div>
                                  
                                  {/* Confidence score */}
                                  <div className="flex items-center gap-2 shrink-0">
                                    <span className="text-[9px] text-muted-foreground font-bold uppercase">Confidence</span>
                                    <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-lg ${
                                      fact.confidence >= 0.9 ? "bg-green-500/10 text-green-500" : "bg-amber-500/10 text-amber-500"
                                    }`}>
                                      {Math.round(fact.confidence * 100)}%
                                    </span>
                                  </div>
                                </div>

                                {/* Evidence verbatim */}
                                {fact.evidence_verbatim && (
                                  <div className="p-3 bg-background/50 border border-border/40 rounded-xl flex gap-2">
                                    <Info className="w-3.5 h-3.5 text-muted-foreground shrink-0 mt-0.5" />
                                    <div className="min-w-0">
                                      <span className="text-[9px] text-muted-foreground font-bold uppercase block tracking-wider">Source Evidence Verbatim</span>
                                      <p className="text-xs italic text-muted-foreground mt-0.5 truncate max-w-full" title={fact.evidence_verbatim}>
                                        "{fact.evidence_verbatim}"
                                      </p>
                                    </div>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Footer buttons */}
                <div className="p-6 border-t border-border bg-muted/10 flex justify-end gap-2">
                  <button
                    onClick={() => setSelectedChunk(null)}
                    className="px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/95 text-xs font-bold rounded-xl transition-all shadow-sm"
                  >
                    Done Inspecting
                  </button>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
