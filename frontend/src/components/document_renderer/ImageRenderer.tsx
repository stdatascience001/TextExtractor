import React from "react";
import { BlockItem, useDocumentContext } from "./DocumentContext";

interface ImageRendererProps {
  item: BlockItem;
}

export const ImageRenderer: React.FC<ImageRendererProps> = ({ item }) => {
  const { selectedBlockId, selectBlock } = useDocumentContext();
  const isSelected = selectedBlockId === item.block_id;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    selectBlock(item.block_id, item.page_number);
  };

  const getAbsoluteUrl = (path: string | null) => {
    if (!path) return "";
    return path.startsWith("http") ? path : `http://127.0.0.1:8000${path}`;
  };

  const imgSrc = getAbsoluteUrl(item.image_path || (item.metadata && item.metadata.image_path));

  if (!imgSrc) return null;

  return (
    <figure
      onClick={handleClick}
      className={`my-4 flex flex-col items-center gap-2 border border-border bg-card p-3 rounded-xl shadow-sm cursor-pointer hover:bg-primary/5 transition-all ${
        isSelected ? "ring-2 ring-primary bg-primary/5" : ""
      }`}
    >
      <img
        src={imgSrc}
        alt="Visual element crop"
        className="rounded-lg max-h-[300px] object-contain max-w-full border"
      />
    </figure>
  );
};
