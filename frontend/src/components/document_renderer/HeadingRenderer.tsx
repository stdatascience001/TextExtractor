import React from "react";
import { BlockItem, useDocumentContext } from "./DocumentContext";

interface HeadingRendererProps {
  item: BlockItem;
}

export const HeadingRenderer: React.FC<HeadingRendererProps> = ({ item }) => {
  const { selectedBlockId, selectBlock } = useDocumentContext();
  const isSelected = selectedBlockId === item.block_id;
  const level = item.heading_level || 2;
  const Tag = `h${Math.min(6, Math.max(1, level))}` as keyof JSX.IntrinsicElements;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    selectBlock(item.block_id, item.page_number);
  };

  const getHeadingStyle = () => {
    switch (level) {
      case 1:
        return "text-2xl font-extrabold text-foreground mb-4 mt-6 border-b pb-2";
      case 2:
        return "text-xl font-bold text-foreground mb-3 mt-5";
      case 3:
        return "text-lg font-bold text-muted-foreground mb-2 mt-4";
      default:
        return "text-base font-semibold text-muted-foreground mb-2 mt-3";
    }
  };

  return (
    <Tag
      onClick={handleClick}
      className={`${getHeadingStyle()} cursor-pointer transition-all hover:bg-primary/5 p-1 rounded ${
        isSelected ? "bg-primary/10 border-l-2 border-primary pl-2" : ""
      }`}
    >
      {item.text}
    </Tag>
  );
};
