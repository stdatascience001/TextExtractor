import React, { useMemo } from "react";
import { BlockItem, useDocumentContext } from "./DocumentContext";

interface ParagraphRendererProps {
  item: BlockItem;
}

export const ParagraphRenderer: React.FC<ParagraphRendererProps> = ({ item }) => {
  const { selectedBlockId, selectBlock, searchQuery } = useDocumentContext();
  const isSelected = selectedBlockId === item.block_id;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    selectBlock(item.block_id, item.page_number);
  };

  const highlightedText = useMemo(() => {
    if (!searchQuery.trim() || !item.text) return item.text;
    const regex = new RegExp(`(${searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, "gi");
    return item.text.replace(regex, '<mark class="bg-primary/30 text-foreground rounded px-0.5">$1</mark>');
  }, [item.text, searchQuery]);

  return (
    <p
      onClick={handleClick}
      className={`text-foreground/90 leading-relaxed text-sm mb-3 cursor-pointer transition-all hover:bg-primary/5 p-1 rounded whitespace-pre-wrap ${
        isSelected ? "bg-primary/10 border-l-2 border-primary pl-2" : ""
      }`}
      dangerouslySetInnerHTML={searchQuery.trim() ? { __html: highlightedText } : undefined}
    >
      {!searchQuery.trim() ? item.text : undefined}
    </p>
  );
};
