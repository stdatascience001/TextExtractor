// import { useCallback, useState } from "react";
// import { motion, AnimatePresence } from "framer-motion";
// import { Upload, FileText, Image, X } from "lucide-react";

// interface FileDropzoneProps {
//   onFileSelect: (file: File) => void;
//   isLoading: boolean;
//   selectedFile: File | null;
//   onClear: () => void;
// }

// const acceptedTypes = {
//   "application/pdf": [".pdf"],
//   "image/jpeg": [".jpg", ".jpeg"],
//   "image/png": [".png"],
// };

// export function FileDropzone({ onFileSelect, isLoading, selectedFile, onClear }: FileDropzoneProps) {
//   const [isDragging, setIsDragging] = useState(false);

//   const handleDrag = useCallback((e: React.DragEvent) => {
//     e.preventDefault();
//     e.stopPropagation();
//   }, []);

//   const handleDragIn = useCallback((e: React.DragEvent) => {
//     e.preventDefault();
//     e.stopPropagation();
//     if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
//       setIsDragging(true);
//     }
//   }, []);

//   const handleDragOut = useCallback((e: React.DragEvent) => {
//     e.preventDefault();
//     e.stopPropagation();
//     setIsDragging(false);
//   }, []);

//   const handleDrop = useCallback(
//     (e: React.DragEvent) => {
//       e.preventDefault();
//       e.stopPropagation();
//       setIsDragging(false);

//       if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
//         const file = e.dataTransfer.files[0];
//         if (isValidFile(file)) {
//           onFileSelect(file);
//         }
//       }
//     },
//     [onFileSelect]
//   );

//   const handleFileInput = useCallback(
//     (e: React.ChangeEvent<HTMLInputElement>) => {
//       if (e.target.files && e.target.files.length > 0) {
//         onFileSelect(e.target.files[0]);
//       }
//     },
//     [onFileSelect]
//   );

//   const isValidFile = (file: File) => {
//     return Object.keys(acceptedTypes).includes(file.type);
//   };

//   const getFileIcon = (file: File) => {
//     if (file.type === "application/pdf") {
//       return <FileText className="w-8 h-8" />;
//     }
//     return <Image className="w-8 h-8" />;
//   };

//   return (
//     <motion.div
//       initial={{ opacity: 0, y: 20 }}
//       animate={{ opacity: 1, y: 0 }}
//       transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
//       className="w-full"
//     >
//       <div
//         onDragEnter={handleDragIn}
//         onDragLeave={handleDragOut}
//         onDragOver={handleDrag}
//         onDrop={handleDrop}
//         className="relative"
//       >
//         <AnimatePresence mode="wait">
//           {selectedFile ? (
//             <motion.div
//               key="selected"
//               initial={{ opacity: 0, scale: 0.95 }}
//               animate={{ opacity: 1, scale: 1 }}
//               exit={{ opacity: 0, scale: 0.95 }}
//               transition={{ duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
//               className="relative surface-elevated rounded-2xl p-6 border border-border"
//             >
//               <div className="flex items-center gap-4">
//                 <motion.div
//                   initial={{ scale: 0 }}
//                   animate={{ scale: 1 }}
//                   transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
//                   className="flex items-center justify-center w-14 h-14 rounded-xl bg-primary/10 text-primary"
//                 >
//                   {getFileIcon(selectedFile)}
//                 </motion.div>
//                 <div className="flex-1 min-w-0">
//                   <motion.p
//                     initial={{ opacity: 0, x: -10 }}
//                     animate={{ opacity: 1, x: 0 }}
//                     transition={{ delay: 0.15 }}
//                     className="font-medium text-foreground truncate"
//                   >
//                     {selectedFile.name}
//                   </motion.p>
//                   <motion.p
//                     initial={{ opacity: 0, x: -10 }}
//                     animate={{ opacity: 1, x: 0 }}
//                     transition={{ delay: 0.2 }}
//                     className="text-sm text-muted-foreground"
//                   >
//                     {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
//                   </motion.p>
//                 </div>
//                 {!isLoading && (
//                   <motion.button
//                     initial={{ opacity: 0, scale: 0 }}
//                     animate={{ opacity: 1, scale: 1 }}
//                     transition={{ delay: 0.25 }}
//                     onClick={onClear}
//                     className="p-2 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
//                   >
//                     <X className="w-5 h-5" />
//                   </motion.button>
//                 )}
//               </div>
              
//               {isLoading && (
//                 <motion.div
//                   initial={{ opacity: 0, height: 0 }}
//                   animate={{ opacity: 1, height: "auto" }}
//                   transition={{ delay: 0.1 }}
//                   className="mt-4"
//                 >
//                   <div className="h-2 rounded-full bg-muted overflow-hidden">
//                     <motion.div
//                       initial={{ x: "-100%" }}
//                       animate={{ x: "100%" }}
//                       transition={{
//                         repeat: Infinity,
//                         duration: 1.5,
//                         ease: "linear",
//                       }}
//                       className="h-full w-1/3 bg-gradient-to-r from-transparent via-primary to-transparent"
//                     />
//                   </div>
//                   <p className="text-sm text-muted-foreground mt-2 text-center">
//                     Extracting text from document...
//                   </p>
//                 </motion.div>
//               )}
//             </motion.div>
//           ) : (
//             <motion.label
//               key="dropzone"
//               initial={{ opacity: 0, scale: 0.95 }}
//               animate={{ opacity: 1, scale: 1 }}
//               exit={{ opacity: 0, scale: 0.95 }}
//               transition={{ duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
//               className={`
//                 relative flex flex-col items-center justify-center
//                 min-h-[280px] rounded-2xl border-2 border-dashed cursor-pointer
//                 transition-all duration-300 ease-out
//                 ${isDragging 
//                   ? "border-primary bg-primary/5 scale-[1.02] shadow-glow" 
//                   : "border-border hover:border-primary/50 hover:bg-muted/30"
//                 }
//               `}
//             >
//               <input
//                 type="file"
//                 accept=".pdf,.jpg,.jpeg,.png"
//                 onChange={handleFileInput}
//                 className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
//               />
              
//               <motion.div
//                 animate={isDragging ? { scale: 1.1, y: -5 } : { scale: 1, y: 0 }}
//                 transition={{ type: "spring", stiffness: 300 }}
//                 className={`
//                   flex items-center justify-center w-16 h-16 rounded-2xl mb-4
//                   transition-colors duration-300
//                   ${isDragging ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}
//                 `}
//               >
//                 <Upload className="w-8 h-8" />
//               </motion.div>

//               <motion.div
//                 animate={isDragging ? { y: -3 } : { y: 0 }}
//                 className="text-center"
//               >
//                 <p className="text-lg font-medium text-foreground mb-1">
//                   {isDragging ? "Drop your file here" : "Drag & drop your document"}
//                 </p>
//                 <p className="text-sm text-muted-foreground">
//                   or click to browse • PDF, JPG, PNG
//                 </p>
//               </motion.div>

//               <AnimatePresence>
//                 {isDragging && (
//                   <motion.div
//                     initial={{ opacity: 0 }}
//                     animate={{ opacity: 1 }}
//                     exit={{ opacity: 0 }}
//                     className="absolute inset-0 rounded-2xl bg-primary/5 pointer-events-none"
//                   />
//                 )}
//               </AnimatePresence>
//             </motion.label>
//           )}
//         </AnimatePresence>
//       </div>
//     </motion.div>
//   );
// }


import { useCallback, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, Image, X } from "lucide-react";
import { Tooltip } from "@/components/ui/Tooltip";
import { toast } from "sonner";

export interface SelectedDocument {
  file: File;
  fileUrl: string;
  fileName: string;
  fileType: "pdf" | "image" | "docx" | "text";
}

interface FileDropzoneProps {
  onFileSelect: (document: SelectedDocument) => void;
  isLoading: boolean;
  selectedFile: File | null;
  onClear: () => void;
}

const acceptedTypes = {
  "application/pdf": [".pdf"],
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "text/plain": [".txt"],
  "text/csv": [".csv"],
};

export function FileDropzone({
  onFileSelect,
  isLoading,
  selectedFile,
  onClear,
}: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  // ✅ Create previewable document
  const createDocument = (file: File): SelectedDocument => {
    const ext = file.name.split('.').pop()?.toLowerCase() || "";
    let type: "pdf" | "image" | "docx" | "text" = "pdf";
    if (file.type.startsWith("image/") || ["jpg", "jpeg", "png"].includes(ext)) {
      type = "image";
    } else if (file.type === "application/pdf" || ext === "pdf") {
      type = "pdf";
    } else if (ext === "docx") {
      type = "docx";
    } else {
      type = "text";
    }
    return {
      file,
      fileUrl: URL.createObjectURL(file),
      fileName: file.name,
      fileType: type,
    };
  };

  const isValidFile = (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    const validExtensions = ["pdf", "jpg", "jpeg", "png", "docx", "txt", "csv"];
    return Object.keys(acceptedTypes).includes(file.type) || (ext && validExtensions.includes(ext));
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragIn = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.items?.length) {
      setIsDragging(true);
    }
  }, []);

  const handleDragOut = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const file = e.dataTransfer.files?.[0];
      if (file) {
        if (isValidFile(file)) {
          onFileSelect(createDocument(file));
        } else {
          toast.error("Unsupported file format", {
            description: "Please upload a PDF, JPG, PNG, DOCX, TXT, or CSV file."
          });
        }
      }
    },
    [onFileSelect]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        if (isValidFile(file)) {
          onFileSelect(createDocument(file));
        } else {
          toast.error("Unsupported file format", {
            description: "Please upload a PDF, JPG, PNG, DOCX, TXT, or CSV file."
          });
        }
      }
    },
    [onFileSelect]
  );

  const getFileIcon = (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (file.type === "application/pdf" || ext === "pdf") {
      return <FileText className="w-8 h-8" />;
    }
    if (ext === "docx" || ext === "txt" || ext === "csv") {
      return <FileText className="w-8 h-8 text-blue-500" />;
    }
    return <Image className="w-8 h-8" />;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="w-full"
    >
      <div
        onDragEnter={handleDragIn}
        onDragLeave={handleDragOut}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className="relative"
      >
        <AnimatePresence mode="wait">
          {selectedFile ? (
            <motion.div
              key="selected"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className="relative surface-elevated rounded-2xl p-6 border border-border"
            >
              <div className="flex items-center gap-4">
                <div className="flex items-center justify-center w-14 h-14 rounded-xl bg-primary/10 text-primary">
                  {getFileIcon(selectedFile)}
                </div>

                <div className="flex-1 min-w-0">
                  <p className="font-medium text-foreground truncate">
                    {selectedFile.name}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>

                {!isLoading && (
                  <Tooltip title="Clear File" description="Remove the selected file and upload a different one." placement="bottom">
                    <button
                      onClick={onClear}
                      className="p-2 rounded-lg hover:bg-muted transition-colors"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </Tooltip>
                )}
              </div>

              {isLoading && (
                <div className="mt-4">
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <motion.div
                      initial={{ x: "-100%" }}
                      animate={{ x: "100%" }}
                      transition={{
                        repeat: Infinity,
                        duration: 1.5,
                        ease: "linear",
                      }}
                      className="h-full w-1/3 bg-gradient-to-r from-transparent via-primary to-transparent"
                    />
                  </div>
                  <p className="text-sm text-muted-foreground mt-2 text-center">
                    Extracting text from document…
                  </p>
                </div>
              )}
            </motion.div>
          ) : (
            <motion.label
              key="dropzone"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className={`relative flex flex-col items-center justify-center
                min-h-[280px] rounded-2xl border-2 border-dashed cursor-pointer
                transition-all
                ${
                  isDragging
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50 hover:bg-muted/30"
                }`}
            >
              <input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.docx,.txt,.csv"
                onChange={handleFileInput}
                title=""
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />

              <div
                className={`flex items-center justify-center w-16 h-16 rounded-2xl mb-4
                  ${
                    isDragging
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                  }`}
              >
                <Upload className="w-8 h-8" />
              </div>

              <div className="text-center">
                <p className="text-lg font-medium mb-1">
                  {isDragging
                    ? "Drop your file here"
                    : "Drag & drop your document"}
                </p>
                <p className="text-sm text-muted-foreground">
                  or click to browse • PDF, JPG, PNG, DOCX, TXT, CSV
                </p>
              </div>
            </motion.label>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
