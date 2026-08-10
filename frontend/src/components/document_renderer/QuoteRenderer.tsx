import React from "react";
import { BlockItem, useDocumentContext } from "./DocumentContext";

interface QuoteRendererProps {
  item: BlockItem;
}

export const QuoteRenderer: React.FC<QuoteRendererProps> = ({ item }) => {
  const { selectedBlockId, selectBlock } = useDocumentContext();
  const isSelected = selectedBlockId === item.block_id;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    selectBlock(item.block_id, item.page_number);
  };

  return (
    <blockquote
      onClick={handleClick}
      className={`pl-4 my-4 border-l-4 border-muted-foreground/30 italic text-muted-foreground cursor-pointer hover:bg-primary/5 transition-all p-1 rounded ${
        isSelected ? "bg-primary/10 border-l-primary" : ""
      }`}
    >
      <p className="text-sm leading-relaxed">{item.text}</p>
    </blockquote>
  );
};
