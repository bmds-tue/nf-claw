"use client";

import { motion } from "framer-motion";
import { EASE } from "@/lib/motion";

/** Each route fades and settles in as it mounts, so moving between pages never feels like a cut. */
export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={false}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}
