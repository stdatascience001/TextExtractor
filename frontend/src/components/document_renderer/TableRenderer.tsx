import React from "react";
import { BlockItem, useDocumentContext } from "./DocumentContext";

interface TableRendererProps {
  item: BlockItem;
}

export const TableRenderer: React.FC<TableRendererProps> = ({ item }) => {
  const { selectedBlockId, selectBlock } = useDocumentContext();
  const isSelected = selectedBlockId === item.block_id;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    selectBlock(item.block_id, item.page_number);
  };

  const tableHtml = item.table_html || "";

  return (
    <div
      onClick={handleClick}
      className={`my-4 overflow-x-auto rounded-xl border border-border bg-card/50 backdrop-blur-sm cursor-pointer hover:bg-primary/5 transition-all p-2 ${
        isSelected ? "ring-2 ring-primary bg-primary/5" : ""
      }`}
    >
      <div 
        className="prose prose-sm max-w-none text-foreground table-renderer-container"
        dangerouslySetInnerHTML={{ __html: tableHtml }}
      />
    </div>
  );
};
