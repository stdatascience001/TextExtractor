import React from "react";
import { BlockItem } from "./DocumentContext";
import { HeadingRenderer } from "./HeadingRenderer";
import { ParagraphRenderer } from "./ParagraphRenderer";
import { TableRenderer } from "./TableRenderer";
import { ImageRenderer } from "./ImageRenderer";
import { ListRenderer } from "./ListRenderer";
import { CodeRenderer } from "./CodeRenderer";
import { QuoteRenderer } from "./QuoteRenderer";
import { FormulaRenderer } from "./FormulaRenderer";
import { FootnoteRenderer } from "./FootnoteRenderer";
import { CaptionRenderer } from "./CaptionRenderer";

interface BlockRendererProps {
  item: BlockItem;
}

export const BlockRenderer: React.FC<BlockRendererProps> = ({ item }) => {
  // Select matching subcomponent based on type
  const renderItem = () => {
    switch (item.type) {
      case "heading":
        return <HeadingRenderer item={item} />;
      case "table":
        return <TableRenderer item={item} />;
      case "image":
        return <ImageRenderer item={item} />;
      case "bullet_list":
      case "numbered_list":
        return <ListRenderer item={item} />;
      case "code":
        return <CodeRenderer item={item} />;
      case "quote":
        return <QuoteRenderer item={item} />;
      case "caption":
        return <CaptionRenderer item={item} />;
      case "formula":
        return <FormulaRenderer item={item} />;
      case "footnote":
        return <FootnoteRenderer item={item} />;
      case "paragraph":
      default:
        // Ignore structural empty layouts like header/footer if they have no text
        if ((item.type === "header" || item.type === "footer") && !item.text) {
          return null;
        }
        return <ParagraphRenderer item={item} />;
    }
  };

  const renderedSelf = renderItem();

  // Recursively render nested children
  const hasChildren = item.children && item.children.length > 0;

  return (
    <div className="block-node-wrapper">
      {renderedSelf}
      {hasChildren && (
        <div className="pl-4 border-l border-border/40 ml-2 mt-1 space-y-1 block-node-children">
          {item.children.map((child) => (
            <BlockRenderer key={child.block_id} item={child} />
          ))}
        </div>
      )}
    </div>
  );
};
