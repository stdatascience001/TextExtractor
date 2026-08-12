import React, { useState } from "react";
import { Link2, Loader2, Sparkles, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/use-toast";
import { useNavigate } from "react-router-dom";
import { Tooltip } from "./ui/Tooltip";

export function GoogleSheetImport() {
  const [url, setUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    // Basic client validation
    if (!url.includes("docs.google.com/spreadsheets")) {
      toast({
        variant: "destructive",
        title: "Invalid URL",
        description: "Please enter a valid Google Sheets link.",
      });
      return;
    }

    setIsLoading(false);
    setIsLoading(true);

    try {
      const activeProjectId = localStorage.getItem("activeProjectId") || undefined;
      const result = await api.importGoogleSheet(url, activeProjectId);

      toast({
        title: "Import Successful",
        description: "Google Sheet processing has been queued in the background.",
      });

      // Redirect to view document page
      setTimeout(() => {
        navigate(`/documents/${result.document_id}`);
      }, 1500);
    } catch (err: any) {
      toast({
        variant: "destructive",
        title: "Import Failed",
        description: err.message || "Failed to import public Google Sheet.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-card rounded-2xl p-6 border border-border shadow-soft space-y-4">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-emerald-500/10 text-emerald-500 rounded-xl">
          <Sparkles className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-foreground">Import from Google Sheets</h3>
          <p className="text-[10px] text-muted-foreground mt-0.5">
            Paste a link to any public Google Sheet to import its data
          </p>
        </div>
      </div>

      <form onSubmit={handleImport} className="flex gap-2">
        <div className="relative flex-1">
          <Link2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="url"
            placeholder="https://docs.google.com/spreadsheets/d/.../edit"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={isLoading}
            className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-muted/60 border border-transparent focus:border-emerald-500/50 focus:bg-background outline-none transition-all text-xs"
          />
        </div>
        <Tooltip content="Import Sheet Data" position="top">
          <button
            type="submit"
            disabled={isLoading || !url.trim()}
            className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-muted disabled:text-muted-foreground text-white text-xs font-semibold rounded-xl transition-all shadow-sm flex items-center gap-2 duration-150 active:scale-95 cursor-pointer shrink-0"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Importing...
              </>
            ) : (
              "Import"
            )}
          </button>
        </Tooltip>
      </form>

      <div className="flex items-start gap-2 text-[10px] text-muted-foreground bg-muted/40 p-3 rounded-xl border border-border/40">
        <AlertCircle className="w-3.5 h-3.5 text-primary mt-0.5 shrink-0" />
        <span>
          Make sure your sheet settings are configured to <b>"Anyone with the link can view"</b> before importing.
        </span>
      </div>
    </div>
  );
}
