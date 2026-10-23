"use client";

import { motion, useReducedMotion } from "framer-motion";
import { EASE } from "@/lib/motion";

/** Each route fades and settles in as it mounts, so moving between pages never feels like a cut. */
export default function Template({ children }: { children: React.ReactNode }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}
