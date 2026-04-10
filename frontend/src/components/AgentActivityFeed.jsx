/**
 * AgentActivityFeed — shows real-time agent pipeline progress via SSE events.
 */
import { FiCheckCircle, FiLoader, FiCircle } from "react-icons/fi";

const STATUS_CONFIG = {
  done: {
    icon: <FiCheckCircle className="w-5 h-5 text-emerald-600" />,
    textClass: "text-emerald-600",
  },
  loading: {
    icon: <FiLoader className="w-5 h-5 text-blue-600 animate-spin" />,
    textClass: "text-blue-600 font-medium",
  },
  pending: {
    icon: <FiCircle className="w-5 h-5 text-slate-300" />,
    textClass: "text-slate-400",
  },
};

export default function AgentActivityFeed({ steps }) {
  return (
    <div className="max-w-lg mx-auto bg-white rounded-xl shadow-md p-6 space-y-4">
      <h2 className="text-lg font-semibold font-lexend text-slate-900 flex items-center gap-2 justify-center">
        Processing your query...
      </h2>
      <ul className="space-y-3">
        {steps.map((step) => {
          const config = STATUS_CONFIG[step.status] || STATUS_CONFIG.pending;
          return (
            <li
              key={step.key}
              className={`flex items-center gap-3 ${config.textClass}`}
            >
              {config.icon}
              <span className="text-sm">
                {step.icon} {step.label}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
