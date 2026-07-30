// import { motion } from "framer-motion";
// import { FileText, Image } from "lucide-react";
// import type { ExtractedDocument } from "@/lib/mockApi";

// interface DocumentViewerProps {
//   document: ExtractedDocument;
//   currentPage: number;
// }

// export function DocumentViewer({ document, currentPage }: DocumentViewerProps) {
//   const isPdf = document.fileType === "pdf";

//   return (
//     <motion.div
//       initial={{ opacity: 0 }}
//       animate={{ opacity: 1 }}
//       transition={{ duration: 0.4 }}
//       className="h-full flex flex-col"
//     >
//       <div className="flex-1 relative rounded-xl overflow-hidden bg-surface-sunken border border-border">
//         {isPdf ? (
//           <motion.div
//             key={`pdf-${currentPage}`}
//             initial={{ opacity: 0, y: 10 }}
//             animate={{ opacity: 1, y: 0 }}
//             transition={{ duration: 0.3 }}
//             className="absolute inset-0 flex items-center justify-center"
//           >
//             <div className="text-center p-8">
//               <motion.div
//                 initial={{ scale: 0.8 }}
//                 animate={{ scale: 1 }}
//                 transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
//                 className="w-24 h-32 mx-auto mb-4 rounded-lg bg-card shadow-soft border border-border flex items-center justify-center"
//               >
//                 <FileText className="w-12 h-12 text-primary" />
//               </motion.div>
//               <motion.p
//                 initial={{ opacity: 0 }}
//                 animate={{ opacity: 1 }}
//                 transition={{ delay: 0.2 }}
//                 className="text-sm text-muted-foreground"
//               >
//                 PDF Preview
//               </motion.p>
//               <motion.p
//                 initial={{ opacity: 0 }}
//                 animate={{ opacity: 1 }}
//                 transition={{ delay: 0.25 }}
//                 className="text-xs text-muted-foreground mt-1"
//               >
//                 Page {currentPage} of {document.pages.length}
//               </motion.p>
//             </div>
//           </motion.div>
//         ) : (
//           <motion.img
//             key="image"
//             initial={{ opacity: 0, scale: 1.02 }}
//             animate={{ opacity: 1, scale: 1 }}
//             transition={{ duration: 0.4 }}
//             src={document.fileUrl}
//             alt={document.fileName}
//             className="w-full h-full object-contain"
//           />
//         )}

//         {/* Page indicator overlay */}
//         <motion.div
//           initial={{ opacity: 0, y: 10 }}
//           animate={{ opacity: 1, y: 0 }}
//           transition={{ delay: 0.3 }}
//           className="absolute bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-full bg-foreground/80 backdrop-blur-sm"
//         >
//           <span className="text-sm font-medium text-background">
//             {document.fileName}
//           </span>
//         </motion.div>
//       </div>
//     </motion.div>
//   );
// }


import { motion, AnimatePresence } from "framer-motion";
import { FileText, Image as ImageIcon, AlertTriangle } from "lucide-react";
import type { ExtractedDocument } from "@/lib/mockApi";

interface DocumentViewerProps {
  document: ExtractedDocument;
  currentPage: number;
}

export function DocumentViewer({
  document,
  currentPage,
}: DocumentViewerProps) {
  const currentPageData = document.pages[currentPage - 1];
  
  // Ensure we use the absolute URL for the backend API
  const getAbsoluteUrl = (url: string) => {
    if (!url) return "";
    return url.startsWith("http") ? url : `http://localhost:8000${url}`;
  };

  const fileUrl = getAbsoluteUrl(document.fileUrl);
  const imageUrl = currentPageData?.imageUrl ? getAbsoluteUrl(currentPageData.imageUrl) : fileUrl;
  const isPdf = document.fileType === "pdf";

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="h-full flex flex-col gap-4"
    >
      {/* ===== Preview Section ===== */}
      <div className="flex-1 relative rounded-xl overflow-hidden bg-surface-sunken border border-border">
        <AnimatePresence mode="wait">
          {isPdf ? (
            <motion.iframe
              key={fileUrl}
              src={`${fileUrl}#view=FitH`}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.02 }}
              transition={{ duration: 0.3 }}
              className="w-full h-full border-none"
              title={`${document.fileName} - PDF Preview`}
            />
          ) : (
            <motion.img
              key={imageUrl}
              src={imageUrl}
              alt={`${document.fileName} - Page ${currentPage}`}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.02 }}
              transition={{ duration: 0.3 }}
              className="w-full h-full object-contain"
            />
          )}
        </AnimatePresence>

        {/* File name and page badge */}
        {!isPdf && (
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-full bg-foreground/80 backdrop-blur-sm border border-white/10 flex items-center gap-2">
            <span className="text-sm font-medium text-background">
              {document.fileName}
            </span>
            <span className="w-1 h-1 rounded-full bg-background/50" />
            <span className="text-xs font-bold text-background/80">
              PAGE {currentPage}
            </span>
          </div>
        )}
      </div>
    </motion.div>
  );
}

