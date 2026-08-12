import React, { useState, useMemo } from "react";
import { Table, Search, AlertCircle, ArrowUpDown } from "lucide-react";
import type { ExtractedDocument } from "@/lib/mockApi";

interface SpreadsheetRendererProps {
  document: ExtractedDocument;
  currentPage: number;
  onPageChange?: (page: number) => void;
}

export function SpreadsheetRenderer({
  document,
  currentPage,
  onPageChange,
}: SpreadsheetRendererProps) {
  const [filterQuery, setFilterQuery] = useState("");
  const [sortColumn, setSortColumn] = useState<number | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  // Fetch structured pages from metadata if available
  const pages = document.structuredData?.document?.pages || [];
  const activePage = pages[currentPage - 1];

  // Retrieve table element on the active page
  const tableItem = activePage?.items?.find((item) => item.type === "table");
  const headers: string[] = tableItem?.metadata?.headers || [];
  const rawRows: string[][] = tableItem?.metadata?.rows || [];

  // Warn on large sheets
  const rowLimit = 1000;
  const isCapped = rawRows.length > rowLimit;
  const displayRows = useMemo(() => {
    return isCapped ? rawRows.slice(0, rowLimit) : rawRows;
  }, [rawRows, isCapped]);

  // Handle local text filtering
  const filteredRows = useMemo(() => {
    if (!filterQuery.trim()) return displayRows;
    const query = filterQuery.toLowerCase();
    return displayRows.filter((row) =>
      row.some((cell) => String(cell).toLowerCase().includes(query))
    );
  }, [displayRows, filterQuery]);

  // Handle column-level sorting
  const handleSort = (colIndex: number) => {
    if (sortColumn === colIndex) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(colIndex);
      setSortDirection("asc");
    }
  };

  const sortedRows = useMemo(() => {
    if (sortColumn === null) return filteredRows;
    return [...filteredRows].sort((a, b) => {
      const valA = a[sortColumn] ?? "";
      const valB = b[sortColumn] ?? "";

      const numA = Number(valA);
      const numB = Number(valB);

      if (!isNaN(numA) && !isNaN(numB)) {
        return sortDirection === "asc" ? numA - numB : numB - numA;
      }

      return sortDirection === "asc"
        ? String(valA).localeCompare(String(valB))
        : String(valB).localeCompare(String(valA));
    });
  }, [filteredRows, sortColumn, sortDirection]);

  // Get sheet list names for the tabs selector
  const sheetTabs = useMemo(() => {
    return pages.map((page, idx) => {
      const headerItem = page.items?.find((item) => item.type === "sheet_header");
      const sheetName =
        headerItem?.metadata?.sheet_name ||
        headerItem?.text?.replace("Sheet: ", "") ||
        `Sheet ${idx + 1}`;
      return {
        pageNumber: page.page_number,
        sheetName,
      };
    });
  }, [pages]);

  return (
    <div className="h-full flex flex-col gap-4 bg-card rounded-xl border border-border shadow-soft overflow-hidden select-none">
      
      {/* 📊 Worksheet Tab Selector */}
      {sheetTabs.length > 1 && (
        <div className="flex border-b border-border bg-muted/20 overflow-x-auto custom-scrollbar p-1.5 gap-1 shrink-0">
          {sheetTabs.map((tab) => {
            const isActive = tab.pageNumber === currentPage;
            return (
              <button
                key={tab.pageNumber}
                onClick={() => onPageChange?.(tab.pageNumber)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all duration-150 ${
                  isActive
                    ? "bg-background text-primary shadow-sm border border-border"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
                }`}
              >
                <Table className="w-3.5 h-3.5" />
                {tab.sheetName}
              </button>
            );
          })}
        </div>
      )}

      {/* 🔍 Local Search & Warning Banner */}
      <div className="px-4 pt-1 flex flex-col md:flex-row md:items-center justify-between gap-4 shrink-0">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search rows in active sheet..."
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-muted/60 border border-transparent focus:border-primary/50 focus:bg-background outline-none transition-all text-xs"
          />
        </div>

        {isCapped && (
          <div className="flex items-center gap-2 text-[10px] font-medium text-amber-600 bg-amber-50 dark:bg-amber-950/20 border border-amber-200/30 px-3 py-1.5 rounded-lg">
            <AlertCircle className="w-3.5 h-3.5" />
            Showing first {rowLimit} rows. Large spreadsheets are fully indexed in vector database.
          </div>
        )}
      </div>

      {/* 📦 Grid Spreadsheet Table */}
      <div className="flex-1 overflow-auto border-t border-border bg-background select-text custom-scrollbar">
        {sortedRows.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full py-12 text-muted-foreground gap-2">
            <Table className="w-8 h-8 opacity-40 animate-pulse text-primary" />
            <span className="text-xs font-semibold">No tabular rows found matching search</span>
          </div>
        ) : (
          <table className="w-full text-left border-collapse text-xs table-fixed">
            <thead className="sticky top-0 bg-card border-b border-border shadow-sm z-10">
              <tr>
                {headers.map((h, idx) => (
                  <th
                    key={idx}
                    onClick={() => handleSort(idx)}
                    className="p-3 font-semibold text-foreground hover:bg-muted/50 cursor-pointer select-none transition-all w-48 border-r border-border/40"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate" title={h}>{h || `Col ${idx + 1}`}</span>
                      <ArrowUpDown className={`w-3.5 h-3.5 shrink-0 transition-opacity ${sortColumn === idx ? "text-primary opacity-100" : "text-muted-foreground opacity-30 hover:opacity-100"}`} />
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/30">
              {sortedRows.map((row, rIdx) => (
                <tr key={rIdx} className="hover:bg-primary/5 transition-colors group">
                  {headers.map((_, cIdx) => {
                    const cellVal = row[cIdx] ?? "";
                    return (
                      <td
                        key={cIdx}
                        className="p-3 text-muted-foreground font-mono truncate border-r border-border/30 group-hover:text-foreground"
                        title={cellVal}
                      >
                        {cellVal}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
