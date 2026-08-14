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
import { FileText, Trash2, Eye, Loader2, Calendar as CalendarIcon, Search, FilterX, SortDesc } from "lucide-react";
import { format } from "date-fns";
import { Calendar } from "../components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "../components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Button } from "../components/ui/button";
import { cn } from "../lib/utils";
import { SidebarLayout } from "@/shared/layouts/SidebarLayout";

export default function MyDocuments() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);
  const [documentToDelete, setDocumentToDelete] = useState<{ id: string, fileName: string } | null>(null);

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
    }, 500);
    return () => clearTimeout(handler);
  }, [query]);

  // Handle filter changes (dates, sort) requiring page reset
  const handleFilterChange = () => {
    setPage(1);
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

  const confirmDelete = async () => {
    if (!documentToDelete) return;
    const { id } = documentToDelete;

    setIsDeleting(id);
    try {
      await api.deleteDocument(id);
      toast({ title: "Deleted", description: "Document deleted successfully." });

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

  const clearFilters = () => {
    setQuery("");
    setStartDate(undefined);
    setEndDate(undefined);
    setSortOption("newest");
    setPage(1);
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <SidebarLayout>
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-8">
          <div>
            <h2 className="text-2xl font-bold text-foreground">Document Dashboard</h2>
            <p className="text-muted-foreground text-sm mt-1">Manage and search your extracted documents</p>
          </div>
          <Link to="/" className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors shadow-sm">
            + New Extraction
          </Link>
        </div>

        {/* Dashboard Filters */}
        <div className="bg-card border border-border rounded-xl p-4 mb-8 shadow-sm">
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

        {/* Results Info */}
        {!loading && (
          <div className="mb-4 text-sm text-muted-foreground">
            Found {total} document{total !== 1 ? 's' : ''}
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
            <button onClick={clearFilters} className="px-4 py-2 bg-primary/10 text-primary rounded-lg text-sm font-medium hover:bg-primary/20 transition-colors">
              Clear all filters
            </button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              <AnimatePresence>
                {documents.map((doc) => (
                  <motion.div
                    key={doc.id}
                    layout
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="bg-card border border-border rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all group"
                  >
                    {/* Thumbnail / Header Area */}
                    <div className="h-32 bg-muted flex items-center justify-center border-b border-border relative overflow-hidden">
                      {doc.file_type === "image" ? (
                        <img
                          src={doc.file_path.startsWith('http') ? doc.file_path : `http://127.0.0.1:8000${doc.file_path}`}
                          alt={doc.file_name}
                          className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                        />
                      ) : (
                        <FileText className="w-12 h-12 text-muted-foreground opacity-50" />
                      )}
                      <div className="absolute top-3 left-3 px-2 py-1 bg-background/80 backdrop-blur-sm rounded text-xs font-medium text-foreground uppercase shadow-sm">
                        {doc.file_type}
                      </div>
                      <div className={`absolute top-3 right-3 px-2 py-1 rounded text-[10px] font-bold uppercase shadow-sm ${doc.status === 'completed' ? 'bg-green-500/90 text-white' :
                        doc.status === 'failed' ? 'bg-red-500/90 text-white' :
                          'bg-yellow-500/90 text-black border border-yellow-300 animate-pulse'
                        }`}>
                        {doc.status || 'uploaded'}
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
                      <div className="flex items-center gap-3">
                        <Link
                          to={`/documents/${doc.id}`}
                          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-primary/10 text-primary rounded-lg text-sm font-medium hover:bg-primary/20 transition-colors"
                        >
                          <Eye className="w-4 h-4" /> View
                        </Link>
                        <button
                          onClick={() => setDocumentToDelete({ id: doc.id, fileName: doc.file_name })}
                          disabled={isDeleting === doc.id}
                          className="p-2 text-destructive hover:bg-destructive/10 rounded-lg transition-colors disabled:opacity-50"
                        >
                          {isDeleting === doc.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-10 flex items-center justify-center gap-4">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 border border-border rounded-lg text-sm font-medium hover:bg-muted disabled:opacity-50 disabled:hover:bg-transparent transition-colors"
                >
                  Previous
                </button>
                <span className="text-sm text-muted-foreground">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-4 py-2 border border-border rounded-lg text-sm font-medium hover:bg-muted disabled:opacity-50 disabled:hover:bg-transparent transition-colors"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>

      <AlertDialog open={!!documentToDelete} onOpenChange={(open) => !open && setDocumentToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{documentToDelete?.fileName}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-transparent border border-input hover:bg-white hover:text-black transition-colors">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </SidebarLayout>
  );
}
