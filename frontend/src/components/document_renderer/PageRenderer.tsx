import React from "react";
import { PageInfo } from "./DocumentContext";
import { BlockRenderer } from "./BlockRenderer";

interface PageRendererProps {
  page: PageInfo;
}

export const PageRenderer: React.FC<PageRendererProps> = ({ page }) => {
  const rootItems = page.items || [];

  return (
    <div className="page-node-container space-y-4 py-2">
      {rootItems.length === 0 ? (
        <p className="text-xs text-muted-foreground italic text-center py-6">
          No structured text content identified on page {page.page_number}.
        </p>
      ) : (
        rootItems.map((item) => (
          <BlockRenderer key={item.block_id} item={item} />
        ))
      )}
    </div>
  );
};
