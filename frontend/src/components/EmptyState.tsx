import { motion } from "framer-motion";
import { FileSearch, Sparkles } from "lucide-react";

export function EmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="h-full flex items-center justify-center"
    >
      <div className="text-center max-w-md px-8">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
          className="relative inline-block mb-6"
        >
          <div className="w-20 h-20 rounded-2xl bg-muted flex items-center justify-center">
            <FileSearch className="w-10 h-10 text-muted-foreground" />
          </div>
          <motion.div
            animate={{ 
              scale: [1, 1.2, 1],
              rotate: [0, 10, -10, 0]
            }}
            transition={{ 
              duration: 2,
              repeat: Infinity,
              repeatDelay: 3
            }}
            className="absolute -top-2 -right-2 w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center"
          >
            <Sparkles className="w-4 h-4 text-primary" />
          </motion.div>
        </motion.div>
        
        <motion.h3
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-xl font-semibold text-foreground mb-2"
        >
          No document selected
        </motion.h3>
        
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-muted-foreground"
        >
          Upload a PDF or image to extract text using AI-powered optical character recognition.
        </motion.p>
      </div>
    </motion.div>
  );
}
