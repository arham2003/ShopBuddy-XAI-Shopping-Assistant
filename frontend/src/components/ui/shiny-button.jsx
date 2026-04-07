import React from "react";
import { motion } from "motion/react";

import { cn } from "@/lib/utils";

export const ShinyButton = React.forwardRef(
  (
    {
      children,
      className,
      background = "#000000",
      textColor = "#ffffff",
      shineColor = "rgba(255,255,255,0.95)",
      ...props
    },
    ref,
  ) => {
    return (
      <motion.button
        ref={ref}
        whileTap={{ scale: 0.97 }}
        className={cn(
          "group relative inline-flex items-center justify-center overflow-hidden rounded-lg border border-white/20 px-6 py-2 font-semibold",
          "transition-all duration-300 ease-out",
          "hover:-translate-y-0.5 hover:shadow-[0_10px_24px_rgba(0,0,0,0.28)]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        style={{
          background,
          color: textColor,
        }}
        {...props}
      >
        <motion.span
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-0 -left-1/2 w-1/2 -skew-x-12 bg-gradient-to-r from-transparent via-white/70 to-transparent"
          style={{
            backgroundImage: `linear-gradient(to right, transparent, ${shineColor}, transparent)`,
          }}
          initial={{ x: "-180%" }}
          animate={{ x: "360%" }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "linear" }}
        />

        <span className="relative z-10 text-sm tracking-wide">{children}</span>

        <span
          aria-hidden="true"
          style={{
            boxShadow: "inset 0 1px 0 rgba(255,255,255,0.18)",
          }}
          className="absolute inset-0 rounded-[inherit]"
        />
      </motion.button>
    );
  },
);

ShinyButton.displayName = "ShinyButton";
