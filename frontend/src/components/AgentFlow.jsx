import React, { useRef } from "react";
import { AnimatedBeam } from "./ui/animated-beam";
import { Search, Bot, ShoppingCart, ShoppingBag } from "lucide-react";

export function AgentFlow() {
  const containerRef = useRef(null);
  const userRef = useRef(null);
  const agentRef = useRef(null);
  const amazonRef = useRef(null);
  const darazRef = useRef(null);

  return (
    <div
      className="relative flex w-full max-w-4xl mx-auto items-center justify-center h-[450px] overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-10 shadow-lg"
      ref={containerRef}
    >
      <div className="flex h-full w-full flex-col justify-between items-center z-10 py-4">
        {/* Top level: User */}
        <div className="flex w-full justify-center">
          <div className="relative flex flex-col items-center">
            <div
              ref={userRef}
              className="flex h-16 w-16 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 shadow-[0_0_20px_-12px_rgba(0,0,0,0.8)] z-10"
            >
              <Search className="h-8 w-8" />
            </div>
            <span className="absolute top-full mt-3 text-sm font-bold text-slate-700 dark:text-slate-200 whitespace-nowrap">
              Your Request
            </span>
          </div>
        </div>

        {/* Middle level: Agent */}
        <div className="flex w-full justify-center">
          <div className="relative flex flex-col items-center">
            <div
              ref={agentRef}
              className="flex h-20 w-20 items-center justify-center rounded-2xl bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-300 shadow-[0_0_20px_-12px_rgba(0,0,0,0.8)] z-10"
            >
              <Bot className="h-10 w-10" />
            </div>
            <span className="absolute top-full mt-3 text-sm font-bold text-slate-700 dark:text-slate-200 whitespace-nowrap">
              ShopBuddy Agents
            </span>
          </div>
        </div>

        {/* Bottom level: Stores */}
        <div className="flex w-full justify-between px-10 md:px-32">
          <div className="relative flex flex-col items-center">
            <div
              ref={amazonRef}
              className="flex h-16 w-16 items-center justify-center rounded-full bg-orange-100 dark:bg-orange-900 text-orange-600 dark:text-orange-300 shadow-[0_0_20px_-12px_rgba(0,0,0,0.8)] z-10"
            >
              <ShoppingCart className="h-8 w-8" />
            </div>
            <span className="absolute top-full mt-3 text-sm font-bold text-slate-700 dark:text-slate-200 whitespace-nowrap">
              Amazon
            </span>
          </div>
          
          <div className="relative flex flex-col items-center">
            <div
              ref={darazRef}
              className="flex h-16 w-16 items-center justify-center rounded-full bg-pink-100 dark:bg-pink-900 text-pink-600 dark:text-pink-300 shadow-[0_0_20px_-12px_rgba(0,0,0,0.8)] z-10"
            >
              <ShoppingBag className="h-8 w-8" />
            </div>
            <span className="absolute top-full mt-3 text-sm font-bold text-slate-700 dark:text-slate-200 whitespace-nowrap">
              Daraz
            </span>
          </div>
        </div>
      </div>

      {/* Query flows down to the Agent */}
      <AnimatedBeam
        containerRef={containerRef}
        fromRef={userRef}
        toRef={agentRef}
        pathColor="rgba(59, 130, 246, 0.2)"
      />
      {/* Agent searches Amazon */}
      <AnimatedBeam
        containerRef={containerRef}
        fromRef={agentRef}
        toRef={amazonRef}
        curvature={75}
        reverse={false}
        pathColor="rgba(249, 115, 22, 0.2)"
        gradientStartColor="#8b5cf6"
        gradientStopColor="#f97316"
      />
      {/* Agent searches Daraz */}
      <AnimatedBeam
        containerRef={containerRef}
        fromRef={agentRef}
        toRef={darazRef}
        curvature={75}
        reverse={false}
        pathColor="rgba(236, 72, 153, 0.2)"
        gradientStartColor="#8b5cf6"
        gradientStopColor="#ec4899"
      />
    </div>
  );
}
