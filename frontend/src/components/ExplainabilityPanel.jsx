/**
 * ExplainabilityPanel — expandable reasoning chain with confidence score.
 */
import { useState } from "react";
import {
  FiChevronDown,
  FiChevronUp,
  FiCheckCircle,
  FiAlertTriangle,
  FiXCircle,
} from "react-icons/fi";

function classifyReason(text) {
  const lower = text.toLowerCase();
  if (
    lower.includes("warning") ||
    lower.includes("caution") ||
    lower.includes("few reviews") ||
    lower.includes("new seller") ||
    lower.includes("limited")
  ) {
    return "warning";
  }
  if (
    lower.includes("fail") ||
    lower.includes("negative") ||
    lower.includes("poor") ||
    lower.includes("low rating") ||
    lower.includes("excluded")
  ) {
    return "danger";
  }
  return "success";
}

function ReasonRow({ text }) {
  const type = classifyReason(text);
  const icons = {
    success: (
      <FiCheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
    ),
    warning: (
      <FiAlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
    ),
    danger: <FiXCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />,
  };
  const colors = {
    success: "text-emerald-600",
    warning: "text-amber-600",
    danger: "text-red-600",
  };

  return (
    <li className={`flex items-start gap-2 ${colors[type]}`}>
      {icons[type]}
      <span className="text-sm">{text}</span>
    </li>
  );
}

export default function ExplainabilityPanel({
  reasoningChain,
  confidenceScore,
  crossPlatformNote,
}) {
  const [open, setOpen] = useState(false);

  if (!reasoningChain?.length) return null;

  // Parse confidence level label
  const pct = Math.round((confidenceScore || 0) * 100);
  const level = pct >= 80 ? "HIGH" : pct >= 50 ? "MEDIUM" : "LOW";
  const levelColor =
    pct >= 80
      ? "text-emerald-600"
      : pct >= 50
        ? "text-amber-600"
        : "text-red-600";
  const barColor =
    pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="mt-3 border-t border-slate-100 pt-3">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-300 rounded"
        aria-label={open ? "Collapse explanation" : "Expand explanation"}
      >
        {open ? (
          <FiChevronUp className="w-4 h-4" />
        ) : (
          <FiChevronDown className="w-4 h-4" />
        )}
        Why this?
      </button>

      {open && (
        <div className="mt-2 space-y-3 animate-fadeIn">
          <ul className="space-y-1.5">
            {reasoningChain.map((reason, i) => (
              <ReasonRow key={i} text={reason} />
            ))}
          </ul>

          {/* Confidence bar */}
          {/* {confidenceScore != null && (
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs font-medium">
                <span className="text-slate-500">AI Confidence</span>
                <span className={levelColor}>
                  {pct}% — {level}
                </span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2">
                <div
                  className={`${barColor} h-2 rounded-full transition-all duration-500`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )} */}

          {/* Cross-platform note */}
          {crossPlatformNote && (
            <div className="bg-indigo-50 text-indigo-700 rounded-lg px-3 py-2 text-sm">
              {crossPlatformNote}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
