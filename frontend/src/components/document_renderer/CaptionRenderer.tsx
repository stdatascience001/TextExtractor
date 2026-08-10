import React from "react";
import { BlockItem, useDocumentContext } from "./DocumentContext";

interface CaptionRendererProps {
  item: BlockItem;
}

export const CaptionRenderer: React.FC<CaptionRendererProps> = ({ item }) => {
  const { selectedBlockId, selectBlock } = useDocumentContext();
  const isSelected = selectedBlockId === item.block_id;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    selectBlock(item.block_id, item.page_number);
  };

  return (
    <figcaption
      onClick={handleClick}
      className={`mt-1 text-xs text-muted-foreground text-center italic cursor-pointer hover:bg-primary/5 transition-all p-1 rounded ${
        isSelected ? "bg-primary/10 border-l-2 border-primary" : ""
      }`}
    >
      {item.text}
    </figcaption>
  );
};
