/**
 * DemoSessions — shows quick-load demo buttons fetched from the backend.
 */
import { useState, useEffect } from "react";
import { getDemoSessions } from "../services/api";

export default function DemoSessions({ onDemoClick }) {
  const [demos, setDemos] = useState([]);

  useEffect(() => {
    getDemoSessions()
      .then((data) => {
        if (Array.isArray(data)) setDemos(data);
      })
      .catch(() => {}); // silently ignore if no demos
  }, []);

  if (!demos.length) return null;

  return (
    <div className="flex flex-wrap items-center justify-center gap-3 mt-4">
      {demos.map((d) => (
        <button
          key={d.session_id}
          onClick={() => onDemoClick(d.query, d.display_currency)}
          className="relative bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-lg px-4 py-2 text-sm font-medium hover:bg-indigo-100 transition-all duration-200"
          aria-label={`Try demo: ${d.query}`}
        >
          <span className="absolute -top-2 -right-2 bg-amber-400 text-amber-900 text-[10px] font-bold px-1.5 py-0.5 rounded-full leading-none">
            ⚡ Instant
          </span>
          ⚡ Try Demo: {d.query}
        </button>
      ))}
    </div>
  );
}
