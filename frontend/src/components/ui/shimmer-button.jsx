import React from "react";

import { cn } from "@/lib/utils";

export const ShimmerButton = React.forwardRef(
  (
    {
      shimmerColor = "#ffffff",
      shimmerSize = "40%",
      shimmerDuration = "2.4s",
      borderRadius = "12px",
      background = "#2563eb",
      className,
      children,
      ...props
    },
    ref,
  ) => {
    return (
      <button
        style={{
          "--shimmer-color": shimmerColor,
          "--radius": borderRadius,
          "--bg": background,
          "--shimmer-size": shimmerSize,
        }}
        className={cn(
          "group relative inline-flex items-center justify-center overflow-hidden whitespace-nowrap",
          "px-6 py-3 text-white font-semibold border border-blue-400/40",
          "[border-radius:var(--radius)] [background:var(--bg)]",
          "shadow-[0_8px_20px_rgba(37,99,235,0.35)]",
          "transition-all duration-300 ease-out",
          "hover:brightness-110 hover:-translate-y-0.5 active:translate-y-0",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/70",
          className,
        )}
        ref={ref}
        {...props}
      >
        <span
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 rounded-[inherit] bg-gradient-to-b from-white/25 to-transparent"
        />

        <span
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-0 -left-1/2 w-[var(--shimmer-size)] -skew-x-12 bg-gradient-to-r from-transparent via-white/60 to-transparent animate-[shimmer-x_2.4s_linear_infinite]"
          style={{
            animationDuration: shimmerDuration,
            backgroundImage: `linear-gradient(to right, transparent, ${shimmerColor}, transparent)`,
          }}
        />

        <span className="relative z-10">{children}</span>

        <div
          aria-hidden="true"
          className="absolute inset-0 rounded-[inherit] ring-1 ring-inset ring-white/15"
        />
      </button>
    );
  },
);

ShimmerButton.displayName = "ShimmerButton";
