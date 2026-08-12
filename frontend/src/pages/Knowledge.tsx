import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";
import { projectApi } from "../modules/projects/api/projectApi";
import { useToast } from "../components/ui/use-toast";
import { SidebarLayout } from "@/shared/layouts/SidebarLayout";
import { motion, AnimatePresence } from "framer-motion";
import {
  Database,
  Search,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RotateCcw,
  Edit2,
  Check,
  X,
  FileText,
  Filter,
  ExternalLink,
  ChevronDown,
  BookOpen,
  SlidersHorizontal
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";

interface Fact {
  id: string;
  subject: {
    id: string | null;
    name: string;
    type: string;
  };
  predicate: string;
  object: string;
  confidence: number;
  status: string;
  evidence: Array<{
    id: string;
    chunk_id: string;
    document_name: string;
    page_number: number;
    text_snippet: string;
  }>;
  created_at: string | null;
}

interface Project {
  id: string;
  name: string;
  description?: string;
}

export default function Knowledge() {
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [facts, setFacts] = useState<Fact[]>([]);
  
  // Filter and search states
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [minConfidence, setMinConfidence] = useState<number>(0);

  // Modification dialog states
  const [editingFact, setEditingFact] = useState<Fact | null>(null);
  const [editPredicate, setEditPredicate] = useState("");
  const [editObject, setEditObject] = useState("");
  const [isSavingEdit, setIsSavingEdit] = useState(false);

  useEffect(() => {
    if (isAuthLoading) return;
    if (!isAuthenticated) {
      navigate("/login");
      return;
    }
    fetchProjects();
  }, [isAuthenticated, isAuthLoading, navigate]);

  useEffect(() => {
    if (selectedProjectId) {
      fetchFacts(selectedProjectId);
    }
  }, [selectedProjectId]);

  const fetchProjects = async () => {
    try {
      const data = await projectApi.getProjects();
      setProjects(data);
      if (data.length > 0) {
        // Auto-select first project
        setSelectedProjectId(data[0].id);
      } else {
        setLoading(false);
      }
    } catch (err: any) {
      toast({
        variant: "destructive",
        title: "Error loading projects",
        description: err.message || "Could not fetch project list"
      });
      setLoading(false);
    }
  };

  const fetchFacts = async (projectId: string) => {
    setLoading(true);
    try {
      const data = await api.getProjectFacts(projectId);
      setFacts(data);
    } catch (err: any) {
      toast({
        variant: "destructive",
        title: "Error loading facts",
        description: err.message || "Failed to load extracted facts"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (factId: string) => {
    try {
      const updatedFact = await api.approveFact(factId);
      setFacts(prev => prev.map(f => f.id === factId ? { ...f, status: "verified" } : f));
      toast({
        title: "Fact Approved",
        description: "The claim status has been successfully updated to verified."
      });
    } catch (err: any) {
      toast({
        variant: "destructive",
        title: "Action Failed",
        description: err.message || "Could not approve fact"
      });
    }
  };

  const handleReject = async (factId: string) => {
    try {
      const updatedFact = await api.rejectFact(factId);
      setFacts(prev => prev.map(f => f.id === factId ? { ...f, status: "rejected" } : f));
      toast({
        title: "Fact Rejected",
        description: "The claim status has been updated to rejected."
      });
    } catch (err: any) {
      toast({
        variant: "destructive",
        title: "Action Failed",
        description: err.message || "Could not reject fact"
      });
    }
  };

  const handleUndo = async (factId: string) => {
    try {
      const restoredFact = await api.undoFactAction(factId);
      setFacts(prev => prev.map(f => f.id === factId ? { ...f, status: restoredFact.status } : f));
      toast({
        title: "Action Reverted",
        description: "The previous verification action was undone successfully."
      });
    } catch (err: any) {
      toast({
        variant: "destructive",
        title: "Action Failed",
        description: err.message || "Could not revert status"
      });
    }
  };

  const startEdit = (fact: Fact) => {
    setEditingFact(fact);
    setEditPredicate(fact.predicate);
    setEditObject(fact.object);
  };

  const saveEdit = async () => {
    if (!editingFact) return;
    setIsSavingEdit(true);
    try {
      const updatedFact = await api.modifyFact(editingFact.id, editPredicate, editObject);
      setFacts(prev => prev.map(f => f.id === editingFact.id ? { 
        ...f, 
        predicate: editPredicate, 
        object: editObject,
        status: updatedFact.status
      } : f));
      setEditingFact(null);
      toast({
        title: "Fact Modified",
        description: "The claim details have been updated."
      });
    } catch (err: any) {
      toast({
        variant: "destructive",
        title: "Modification Failed",
        description: err.message || "Could not update fact claim"
      });
    } finally {
      setIsSavingEdit(false);
    }
  };

  // Filtered facts computation
  const filteredFacts = facts.filter(fact => {
    const matchesSearch = 
      fact.subject.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      fact.subject.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      fact.predicate.toLowerCase().includes(searchQuery.toLowerCase()) ||
      fact.object.toLowerCase().includes(searchQuery.toLowerCase()) ||
      fact.evidence.some(e => e.document_name.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesStatus = statusFilter === "all" || fact.status === statusFilter;
    const matchesConfidence = fact.confidence >= minConfidence;

    return matchesSearch && matchesStatus && matchesConfidence;
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "verified":
        return <CheckCircle2 className="w-5 h-5 text-emerald-500" />;
      case "rejected":
        return <XCircle className="w-5 h-5 text-rose-500" />;
      default:
        return <AlertCircle className="w-5 h-5 text-amber-500" />;
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "verified":
        return "bg-emerald-500/10 text-emerald-500 border-emerald-500/20";
      case "rejected":
        return "bg-rose-500/10 text-rose-500 border-rose-500/20";
      default:
        return "bg-amber-500/10 text-amber-500 border-amber-500/20";
    }
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return "bg-emerald-500";
    if (score >= 0.5) return "bg-amber-500";
    return "bg-rose-500";
  };

  return (
    <SidebarLayout>
      <div className="space-y-8 max-w-7xl mx-auto">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-foreground flex items-center gap-2">
              <BookOpen className="w-6 h-6 text-primary" />
              Knowledge Base
            </h2>
            <p className="text-muted-foreground text-sm mt-1">
              Review, refine, and verify extracted structured relationships and facts.
            </p>
          </div>
          
          {/* Project selector */}
          {projects.length > 0 && (
            <div className="flex items-center gap-3 bg-muted/40 px-3 py-2 rounded-xl border border-border">
              <span className="text-xs text-muted-foreground font-semibold">Active Project:</span>
              <div className="relative">
                <select
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="bg-transparent text-sm font-semibold text-foreground outline-none pr-8 cursor-pointer appearance-none relative z-10"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id} className="bg-background">
                      {p.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 text-muted-foreground absolute right-0 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>
          )}
        </div>

        {projects.length === 0 && !loading && (
          <div className="text-center py-16 bg-card rounded-2xl border border-border shadow-soft">
            <Database className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="font-bold text-lg text-foreground">No projects found</h3>
            <p className="text-sm text-muted-foreground max-w-md mx-auto mt-2">
              You need to create a project and upload documents before facts can be extracted.
            </p>
            <Link
              to="/projects"
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 mt-6 transition-all"
            >
              Go to Projects
            </Link>
          </div>
        )}

        {projects.length > 0 && (
          <>
            {/* Filter controls */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 bg-muted/20 p-4 rounded-2xl border border-border/80">
              <div className="relative lg:col-span-2">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  type="text"
                  placeholder="Search concepts, properties, or source files..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 h-10 w-full"
                />
              </div>

              {/* Status filter pills */}
              <div className="flex gap-1 bg-muted p-1 rounded-xl items-center border border-border">
                {["all", "pending", "verified", "rejected"].map((status) => (
                  <button
                    key={status}
                    onClick={() => setStatusFilter(status)}
                    className={`flex-1 px-3 py-1.5 rounded-lg text-xs font-bold capitalize transition-all ${
                      statusFilter === status
                        ? "bg-background text-primary shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {status}
                  </button>
                ))}
              </div>

              {/* Confidence threshold slider */}
              <div className="flex items-center gap-4 bg-background/50 px-4 py-1.5 rounded-xl border border-border/80">
                <SlidersHorizontal className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <div className="flex-1">
                  <div className="flex justify-between text-[10px] text-muted-foreground font-semibold mb-1">
                    <span>Min Confidence</span>
                    <span>{Math.round(minConfidence * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={minConfidence}
                    onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                    className="w-full h-1 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
                  />
                </div>
              </div>
            </div>

            {/* Facts content */}
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-primary mr-3" />
                <span className="text-sm font-medium text-muted-foreground">Loading facts database...</span>
              </div>
            ) : filteredFacts.length === 0 ? (
              <div className="text-center py-16 bg-card rounded-2xl border border-border/80 shadow-soft">
                <Database className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="font-bold text-lg text-foreground">No extracted facts found</h3>
                <p className="text-sm text-muted-foreground max-w-md mx-auto mt-2">
                  No claims matched your search filters. Try clearing searches or upload more documents to extract knowledge.
                </p>
                <Link
                  to="/"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary rounded-lg text-sm font-medium hover:bg-primary/20 mt-6 transition-all"
                >
                  Upload Documents
                </Link>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <AnimatePresence mode="popLayout">
                  {filteredFacts.map((fact) => (
                    <motion.div
                      layout
                      key={fact.id}
                      initial={{ opacity: 0, y: 15 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ duration: 0.25 }}
                      className="bg-card border border-border rounded-2xl p-5 shadow-soft hover:shadow-medium transition-all flex flex-col justify-between"
                    >
                      {/* Top metadata */}
                      <div className="flex items-start justify-between gap-3 mb-4">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(fact.status)}
                          <Badge variant="outline" className={`text-xs font-bold border ${getStatusBadgeClass(fact.status)}`}>
                            {fact.status}
                          </Badge>
                        </div>

                        {/* Confidence indicator */}
                        <div className="flex items-center gap-2 bg-muted/40 px-2 py-1 rounded-lg">
                          <div className="w-2 h-2 rounded-full bg-emerald-500" style={{ backgroundColor: getConfidenceColor(fact.confidence) }} />
                          <span className="text-[10px] font-bold text-muted-foreground">
                            {Math.round(fact.confidence * 100)}% Confidence
                          </span>
                        </div>
                      </div>

                      {/* Extracted concept details */}
                      <div className="space-y-4 mb-5 flex-1">
                        {/* Concept Triplets */}
                        <div className="grid grid-cols-3 gap-2 items-center bg-muted/20 p-3 rounded-xl border border-border/40">
                          <div className="text-center">
                            <span className="text-[10px] text-muted-foreground font-semibold uppercase block mb-1">Subject</span>
                            <span className="text-sm font-bold text-foreground block truncate" title={fact.subject.name}>
                              {fact.subject.name}
                            </span>
                            <span className="text-[9px] text-muted-foreground font-semibold block capitalize truncate">
                              ({fact.subject.type})
                            </span>
                          </div>

                          <div className="text-center relative">
                            <span className="text-[10px] text-muted-foreground font-semibold uppercase block mb-1">Predicate</span>
                            <span className="text-xs font-semibold px-2 py-0.5 bg-primary/10 text-primary border border-primary/20 rounded-full inline-block truncate max-w-full">
                              {fact.predicate}
                            </span>
                          </div>

                          <div className="text-center">
                            <span className="text-[10px] text-muted-foreground font-semibold uppercase block mb-1">Object</span>
                            <span className="text-sm font-bold text-foreground block truncate" title={fact.object}>
                              {fact.object}
                            </span>
                          </div>
                        </div>

                        {/* Evidence files */}
                        {fact.evidence && fact.evidence.length > 0 && (
                          <div className="space-y-2">
                            <span className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider block">Source Evidence</span>
                            {fact.evidence.map((ev, index) => (
                              <div key={index} className="bg-muted/15 border border-border/45 rounded-xl p-3 space-y-2">
                                <div className="flex items-center justify-between gap-2 text-xs font-semibold text-muted-foreground">
                                  <span className="flex items-center gap-1 text-primary truncate max-w-[200px]">
                                    <FileText className="w-3.5 h-3.5 flex-shrink-0" />
                                    {ev.document_name}
                                  </span>
                                  <span className="bg-muted px-2 py-0.5 rounded text-[10px] flex-shrink-0">
                                    Page {ev.page_number}
                                  </span>
                                </div>
                                <p className="text-xs italic text-foreground leading-relaxed pl-2 border-l-2 border-primary/30">
                                  "{ev.text_snippet}"
                                </p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Verification Actions */}
                      <div className="flex items-center justify-between gap-3 border-t border-border/50 pt-4 flex-shrink-0">
                        {fact.status !== "pending" ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleUndo(fact.id)}
                            className="text-xs font-semibold text-muted-foreground hover:text-foreground flex items-center gap-1.5"
                          >
                            <RotateCcw className="w-3.5 h-3.5" /> Undo Action
                          </Button>
                        ) : (
                          <span className="text-[10px] text-muted-foreground font-medium italic">Pending Verification</span>
                        )}

                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => startEdit(fact)}
                            className="text-xs font-bold h-8 flex items-center gap-1.5"
                          >
                            <Edit2 className="w-3 h-3" /> Edit
                          </Button>

                          {fact.status !== "verified" && (
                            <Button
                              variant="default"
                              size="sm"
                              onClick={() => handleApprove(fact.id)}
                              className="text-xs font-bold h-8 bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5"
                            >
                              <Check className="w-3.5 h-3.5" /> Verify
                            </Button>
                          )}

                          {fact.status !== "rejected" && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleReject(fact.id)}
                              className="text-xs font-bold h-8 text-rose-600 hover:bg-rose-50 border-rose-200 hover:border-rose-300 flex items-center gap-1.5"
                            >
                              <X className="w-3.5 h-3.5" /> Reject
                            </Button>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            )}
          </>
        )}
      </div>

      {/* Edit fact Dialog */}
      <Dialog open={editingFact !== null} onOpenChange={(open) => !open && setEditingFact(null)}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit2 className="w-5 h-5 text-primary" />
              Edit Fact Details
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-muted-foreground uppercase">Subject Concept</label>
              <div className="bg-muted/40 p-2.5 rounded-lg border border-border text-sm font-semibold text-foreground">
                {editingFact?.subject.name} <span className="text-xs text-muted-foreground">({editingFact?.subject.type})</span>
              </div>
            </div>
            
            <div className="space-y-1.5">
              <label htmlFor="predicate" className="text-xs font-bold text-muted-foreground uppercase">Predicate</label>
              <Input
                id="predicate"
                value={editPredicate}
                onChange={(e) => setEditPredicate(e.target.value)}
                placeholder="e.g. treats, indicates, triggers"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="object" className="text-xs font-bold text-muted-foreground uppercase">Object Detail</label>
              <Input
                id="object"
                value={editObject}
                onChange={(e) => setEditObject(e.target.value)}
                placeholder="e.g. Type 2 Diabetes, Once daily, 500mg"
              />
            </div>
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setEditingFact(null)}>
              Cancel
            </Button>
            <Button onClick={saveEdit} disabled={isSavingEdit}>
              {isSavingEdit ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </SidebarLayout>
  );
}
