import React from "react";
import { BlockItem, useDocumentContext } from "./DocumentContext";

interface FormulaRendererProps {
  item: BlockItem;
}

export const FormulaRenderer: React.FC<FormulaRendererProps> = ({ item }) => {
  const { selectedBlockId, selectBlock } = useDocumentContext();
  const isSelected = selectedBlockId === item.block_id;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    selectBlock(item.block_id, item.page_number);
  };

  return (
    <div
      onClick={handleClick}
      className={`my-4 py-3 px-4 text-center bg-muted/30 border border-border/40 rounded-xl cursor-pointer hover:bg-primary/5 transition-all font-serif italic text-base select-all ${
        isSelected ? "ring-2 ring-primary bg-primary/5" : ""
      }`}
    >
      <span className="text-foreground tracking-wide font-medium">{item.text}</span>
    </div>
  );
};
