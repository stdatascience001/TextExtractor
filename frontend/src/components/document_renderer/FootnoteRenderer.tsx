import React from "react";
import { BlockItem, useDocumentContext } from "./DocumentContext";

interface FootnoteRendererProps {
  item: BlockItem;
}

export const FootnoteRenderer: React.FC<FootnoteRendererProps> = ({ item }) => {
  const { selectedBlockId, selectBlock } = useDocumentContext();
  const isSelected = selectedBlockId === item.block_id;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    selectBlock(item.block_id, item.page_number);
  };

  return (
    <div
      onClick={handleClick}
      className={`pl-3 border-l-2 border-muted/50 my-2 text-[11px] text-muted-foreground cursor-pointer hover:bg-primary/5 transition-all p-1 rounded ${
        isSelected ? "bg-primary/10 border-l-primary" : ""
      }`}
    >
      <span className="font-semibold mr-1 select-none">Fn:</span>
      <span>{item.text}</span>
    </div>
  );
};
