import React from "react";
import { BlockItem, useDocumentContext } from "./DocumentContext";

interface ListRendererProps {
  item: BlockItem;
}

export const ListRenderer: React.FC<ListRendererProps> = ({ item }) => {
  const { selectedBlockId, selectBlock } = useDocumentContext();
  const isSelected = selectedBlockId === item.block_id;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    selectBlock(item.block_id, item.page_number);
  };

  const isNumbered = item.type === "numbered_list";

  return (
    <div
      onClick={handleClick}
      className={`flex items-start gap-2 mb-2 cursor-pointer transition-all hover:bg-primary/5 p-1 rounded ${
        isSelected ? "bg-primary/10 border-l-2 border-primary pl-2" : ""
      }`}
    >
      {isNumbered ? (
        <span className="text-primary font-bold text-sm shrink-0 min-w-5 text-right select-none">
          •
        </span>
      ) : (
        <span className="text-primary text-sm shrink-0 min-w-5 text-center select-none">
          •
        </span>
      )}
      <span className="text-foreground/90 leading-relaxed text-sm">
        {item.text}
      </span>
    </div>
  );
};
