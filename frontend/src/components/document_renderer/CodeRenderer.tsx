import React from "react";
import { BlockItem, useDocumentContext } from "./DocumentContext";

interface CodeRendererProps {
  item: BlockItem;
}

export const CodeRenderer: React.FC<CodeRendererProps> = ({ item }) => {
  const { selectedBlockId, selectBlock } = useDocumentContext();
  const isSelected = selectedBlockId === item.block_id;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    selectBlock(item.block_id, item.page_number);
  };

  return (
    <pre
      onClick={handleClick}
      className={`my-3 p-3 bg-muted font-mono text-xs rounded-xl overflow-x-auto border border-border cursor-pointer hover:bg-muted/80 transition-all ${
        isSelected ? "ring-2 ring-primary" : ""
      }`}
    >
      <code className="text-foreground leading-normal">{item.text}</code>
    </pre>
  );
};
