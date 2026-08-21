import { useState, useEffect, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";
import { useToast } from "../components/ui/use-toast";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../components/ui/alert-dialog";
import { LogoutButton } from "../components/LogoutButton";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  Trash2,
  Eye,
  Loader2,
  Calendar as CalendarIcon,
  Search,
  FilterX,
  SortDesc,
  X,
} from "lucide-react";
import { format } from "date-fns";
import { Calendar } from "../components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "../components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Button } from "../components/ui/button";
import { Checkbox } from "../components/ui/checkbox";
import { cn } from "../lib/utils";
import { SidebarLayout } from "@/shared/layouts/SidebarLayout";

export default function MyDocuments() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);
  const [documentToDelete, setDocumentToDelete] = useState<{ id: string; fileName: string } | null>(null);

  // Multi-select state
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [showBulkDeleteConfirm, setShowBulkDeleteConfirm] = useState(false);

  // Filters
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [startDate, setStartDate] = useState<Date>();
  const [endDate, setEndDate] = useState<Date>();
  const [sortOption, setSortOption] = useState("newest");

  const limit = 9;

  const { isAuthenticated, user, logout, isLoading: isAuthLoading } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(query);
      setPage(1); // Reset to page 1 on new search
      setSelectedIds([]); // Clear selection on search
    }, 500);
    return () => clearTimeout(handler);
  }, [query]);

  // Handle filter changes (dates, sort) requiring page reset
  const handleFilterChange = () => {
    setPage(1);
    setSelectedIds([]);
  };

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const skip = (page - 1) * limit;

      let sortBy = "created_at";
      let sortOrder = "desc";
      if (sortOption === "oldest") {
        sortOrder = "asc";
      } else if (sortOption === "az") {
        sortBy = "file_name";
        sortOrder = "asc";
      }

      // Format dates to ISO strings if present
      const formattedStart = startDate ? new Date(startDate).toISOString() : undefined;
      let formattedEnd = undefined;
      if (endDate) {
        // Set to end of the day
        const d = new Date(endDate);
        d.setHours(23, 59, 59, 999);
        formattedEnd = d.toISOString();
      }

      const data = await api.getDocuments(
        skip,
        limit,
        debouncedQuery,
        undefined, // project_id
        formattedStart,
        formattedEnd,
        sortBy,
        sortOrder
      );
      setDocuments(data.documents);
      setTotal(data.total);
    } catch (err: any) {
      toast({ variant: "destructive", title: "Error", description: err.message || "Failed to load documents" });
    } finally {
      setLoading(false);
    }
  }, [page, limit, debouncedQuery, startDate, endDate, sortOption, toast]);

  useEffect(() => {
    if (isAuthLoading) return;

    if (!isAuthenticated) {
      navigate("/login");
    } else {
      fetchDocuments();
    }
  }, [isAuthenticated, isAuthLoading, navigate, fetchDocuments]);

  // Clear selection on page change
  const handlePageChange = (newPage: number) => {
    setSelectedIds([]);
    setPage(newPage);
  };

  // Toggle single document selection
  const toggleSelectDocument = (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  // Toggle select all on current page
  const isAllCurrentPageSelected =
    documents.length > 0 && documents.every((doc) => selectedIds.includes(doc.id));

  const toggleSelectAll = () => {
    if (isAllCurrentPageSelected) {
      setSelectedIds([]);
    } else {
      setSelectedIds(documents.map((doc) => doc.id));
    }
  };

  const confirmDelete = async () => {
    if (!documentToDelete) return;
    const { id } = documentToDelete;

    setIsDeleting(id);
    try {
      await api.deleteDocument(id);
      toast({ title: "Deleted", description: "Document deleted successfully." });
      setSelectedIds((prev) => prev.filter((itemId) => itemId !== id));

      if (documents.length === 1 && page > 1) {
        setPage(page - 1);
      } else {
        fetchDocuments();
      }
    } catch (err: any) {
      toast({ variant: "destructive", title: "Error", description: err.message || "Failed to delete document" });
    } finally {
      setIsDeleting(null);
      setDocumentToDelete(null);
    }
  };

  const confirmBulkDelete = async () => {
    if (selectedIds.length === 0) return;

    setIsBulkDeleting(true);
    try {
      const res = await api.bulkDeleteDocuments(selectedIds);
      toast({
        title: "Bulk Delete Successful",
        description: res.message || `Successfully deleted ${selectedIds.length} document(s).`,
      });

      const deletedCount = selectedIds.length;
      setSelectedIds([]);

      // If all documents on this page are deleted, move to previous page if possible
      if (documents.length <= deletedCount && page > 1) {
        setPage(page - 1);
      } else {
        fetchDocuments();
      }
    } catch (err: any) {
      toast({
        variant: "destructive",
        title: "Bulk Delete Error",
        description: err.message || "Failed to delete selected documents",
      });
    } finally {
      setIsBulkDeleting(false);
      setShowBulkDeleteConfirm(false);
    }
  };

  const clearFilters = () => {
    setQuery("");
    setStartDate(undefined);
    setEndDate(undefined);
    setSortOption("newest");
    setSelectedIds([]);
    setPage(1);
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <SidebarLayout>
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-8">
          <div>
            <h2 className="text-2xl font-bold text-foreground">Document Dashboard</h2>
            <p className="text-muted-foreground text-sm mt-1">Manage, select, and search your extracted documents</p>
          </div>
          <Link
            to="/"
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors shadow-sm"
          >
            + New Extraction
          </Link>
        </div>

        {/* Dashboard Filters */}
        <div className="bg-card border border-border rounded-xl p-4 mb-6 shadow-sm">
          <div className="flex flex-col lg:flex-row gap-4">
            {/* Search Bar */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search by filename..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-background border border-input rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
              />
            </div>

            {/* Date Filters */}
            <div className="flex items-center gap-2">
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant={"outline"}
                    className={cn(
                      "justify-start text-left font-normal bg-background/50 hover:bg-background/80 hover:text-foreground transition-all border-input rounded-lg",
                      !startDate && "text-muted-foreground hover:text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {startDate ? format(startDate, "PPP") : <span>Start date</span>}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={startDate}
                    onSelect={(date) => {
                      setStartDate(date);
                      handleFilterChange();
                    }}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
              <span className="text-muted-foreground text-sm">to</span>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant={"outline"}
                    className={cn(
                      "justify-start text-left font-normal bg-background/50 hover:bg-background/80 hover:text-foreground transition-all border-input rounded-lg",
                      !endDate && "text-muted-foreground hover:text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {endDate ? format(endDate, "PPP") : <span>End date</span>}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={endDate}
                    onSelect={(date) => {
                      setEndDate(date);
                      handleFilterChange();
                    }}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>

            {/* Sort Dropdown */}
            <div className="flex items-center gap-2">
              <Select
                value={sortOption}
                onValueChange={(val) => {
                  setSortOption(val);
                  handleFilterChange();
                }}
              >
                <SelectTrigger className="w-[180px]">
                  <div className="flex items-center gap-2">
                    <SortDesc className="w-4 h-4 text-muted-foreground hidden sm:block" />
                    <SelectValue placeholder="Sort by..." />
                  </div>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="newest">Recent Uploads</SelectItem>
                  <SelectItem value="oldest">Oldest First</SelectItem>
                  <SelectItem value="az">A-Z (Filename)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Clear Filters */}
            {(query || startDate || endDate || sortOption !== "newest") && (
              <button
                onClick={clearFilters}
                className="px-3 py-2 text-sm text-destructive hover:bg-destructive/10 rounded-lg transition-colors flex items-center gap-1"
              >
                <FilterX className="w-4 h-4" /> Clear
              </button>
            )}
          </div>
        </div>

        {/* Selection & Batch Action Header */}
        {!loading && documents.length > 0 && (
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-muted/40 border border-border/70 rounded-xl px-4 py-2.5 mb-4 shadow-sm">
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-xs sm:text-sm font-medium text-foreground cursor-pointer select-none">
                <Checkbox
                  checked={isAllCurrentPageSelected}
                  onCheckedChange={toggleSelectAll}
                  aria-label="Select all documents on current page"
                />
                <span>Select All ({documents.length})</span>
              </label>

              {selectedIds.length > 0 && (
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                  {selectedIds.length} selected
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto justify-between sm:justify-end">
              <span className="text-xs text-muted-foreground">
                Found {total} document{total !== 1 ? "s" : ""}
              </span>

              <AnimatePresence>
                {selectedIds.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    className="flex items-center gap-2"
                  >
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedIds([])}
                      className="text-xs text-muted-foreground hover:text-foreground h-8 px-2.5"
                    >
                      <X className="w-3.5 h-3.5 mr-1" /> Deselect
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => setShowBulkDeleteConfirm(true)}
                      className="text-xs font-semibold h-8 px-3 gap-1.5 shadow-sm cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      Delete ({selectedIds.length})
                    </Button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        )}

        {/* Document Grid */}
        {(loading || isAuthLoading) && documents.length === 0 ? (
          <div className="flex items-center justify-center py-20">
            <img src="/favicon1.png" alt="Loading..." className="w-10 h-10 animate-spin" />
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-20 bg-muted/30 rounded-2xl border border-border border-dashed">
            <FileText className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-50" />
            <h3 className="text-lg font-medium text-foreground mb-1">No matches found</h3>
            <p className="text-sm text-muted-foreground mb-4">Try adjusting your search filters or dates.</p>
            <button
              onClick={clearFilters}
              className="px-4 py-2 bg-primary/10 text-primary rounded-lg text-sm font-medium hover:bg-primary/20 transition-colors"
            >
              Clear all filters
            </button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              <AnimatePresence>
                {documents.map((doc) => {
                  const isSelected = selectedIds.includes(doc.id);

                  return (
                    <motion.div
                      key={doc.id}
                      layout
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      onClick={() => toggleSelectDocument(doc.id)}
                      className={cn(
                        "bg-card border rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all group cursor-pointer relative",
                        isSelected
                          ? "border-primary ring-2 ring-primary/40 bg-primary/[0.02]"
                          : "border-border hover:border-border/80"
                      )}
                    >
                      {/* Thumbnail / Header Area */}
                      <div className="h-32 bg-muted flex items-center justify-center border-b border-border relative overflow-hidden">
                        {doc.file_type === "image" ? (
                          <img
                            src={
                              doc.file_path.startsWith("http")
                                ? doc.file_path
                                : `http://127.0.0.1:8000${doc.file_path}`
                            }
                            alt={doc.file_name}
                            className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                          />
                        ) : (
                          <FileText className="w-12 h-12 text-muted-foreground opacity-50" />
                        )}

                        {/* Top-Left Selection Checkbox */}
                        <div
                          className="absolute top-3 left-3 z-10 flex items-center gap-2 bg-background/90 backdrop-blur-md px-2 py-1.5 rounded-lg border border-border/80 shadow-sm"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Checkbox
                            checked={isSelected}
                            onCheckedChange={() => toggleSelectDocument(doc.id)}
                            aria-label={`Select ${doc.file_name}`}
                          />
                          <span className="text-[10px] font-semibold text-foreground uppercase">
                            {doc.file_type}
                          </span>
                        </div>

                        {/* Status Badge */}
                        <div
                          className={`absolute top-3 right-3 px-2 py-1 rounded text-[10px] font-bold uppercase shadow-sm ${
                            doc.status === "completed"
                              ? "bg-green-500/90 text-white"
                              : doc.status === "failed"
                              ? "bg-red-500/90 text-white"
                              : "bg-yellow-500/90 text-black border border-yellow-300 animate-pulse"
                          }`}
                        >
                          {doc.status || "uploaded"}
                        </div>
                      </div>

                      {/* Content */}
                      <div className="p-5">
                        <h3 className="font-semibold text-foreground truncate mb-2" title={doc.file_name}>
                          {doc.file_name}
                        </h3>
                        <div className="flex items-center text-xs text-muted-foreground mb-5">
                          <CalendarIcon className="w-3.5 h-3.5 mr-1.5" />
                          {format(new Date(doc.created_at), "MMM d, yyyy • h:mm a")}
                        </div>

                        {/* Actions */}
                        <div
                          className="flex items-center gap-3"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Link
                            to={`/documents/${doc.id}`}
                            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-primary/10 text-primary rounded-lg text-sm font-medium hover:bg-primary/20 transition-colors"
                          >
                            <Eye className="w-4 h-4" /> View
                          </Link>
                          <button
                            onClick={() =>
                              setDocumentToDelete({ id: doc.id, fileName: doc.file_name })
                            }
                            disabled={isDeleting === doc.id || isBulkDeleting}
                            className="p-2 text-destructive hover:bg-destructive/10 rounded-lg transition-colors disabled:opacity-50 cursor-pointer"
                            title="Delete document"
                          >
                            {isDeleting === doc.id ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Trash2 className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-10 flex items-center justify-center gap-4">
                <button
                  onClick={() => handlePageChange(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 border border-border rounded-lg text-sm font-medium hover:bg-muted disabled:opacity-50 disabled:hover:bg-transparent transition-colors cursor-pointer"
                >
                  Previous
                </button>
                <span className="text-sm text-muted-foreground">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => handlePageChange(Math.min(totalPages, page + 1))}
                  disabled={page === totalPages}
                  className="px-4 py-2 border border-border rounded-lg text-sm font-medium hover:bg-muted disabled:opacity-50 disabled:hover:bg-transparent transition-colors cursor-pointer"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Single Document Delete Modal */}
      <AlertDialog
        open={!!documentToDelete}
        onOpenChange={(open) => !open && setDocumentToDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{documentToDelete?.fileName}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-transparent border border-input hover:bg-muted transition-colors cursor-pointer">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90 cursor-pointer"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Bulk Delete Modal */}
      <AlertDialog
        open={showBulkDeleteConfirm}
        onOpenChange={(open) => !open && !isBulkDeleting && setShowBulkDeleteConfirm(false)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-destructive">
              <Trash2 className="h-5 w-5" />
              Delete {selectedIds.length} Documents?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to permanently delete the <strong>{selectedIds.length}</strong> selected
              document(s)? All extracted pages, layout metadata, and associated storage files will be removed. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              disabled={isBulkDeleting}
              className="bg-transparent border border-input hover:bg-muted transition-colors cursor-pointer"
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmBulkDelete}
              disabled={isBulkDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90 flex items-center gap-2 cursor-pointer"
            >
              {isBulkDeleting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Deleting...
                </>
              ) : (
                `Delete ${selectedIds.length} Document(s)`
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </SidebarLayout>
  );
}
