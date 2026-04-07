/**
 * FollowUpChat — collapsible sticky chat bar with fullscreen mode.
 */
import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import {
  FiSend,
  FiMessageCircle,
  FiChevronDown,
  FiMaximize2,
  FiX,
  FiCheck,
} from "react-icons/fi";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

/**
 * FormattedMessage — renders LLM markdown output as structured React elements.
 * Handles: headings (###), bold (**), italic (*), bullet lists (- / *), numbered
 * lists, and paragraph / line breaks. No external dependencies.
 */
function FormattedMessage({ content }) {
  // Split into blocks on blank lines
  const blocks = content.split(/\n{2,}/);

  return (
    <div className="space-y-2">
      {blocks.map((block, bi) => {
        const lines = block.split("\n").map((l) => l.trimEnd());

        // Heading: ### or ## or #
        if (/^#{1,3}\s/.test(lines[0])) {
          const text = lines[0].replace(/^#{1,3}\s*/, "");
          return (
            <p key={bi} className="font-semibold text-slate-900 text-sm">
              {renderInline(text)}
            </p>
          );
        }

        // Bullet list: lines starting with - or *
        if (lines.every((l) => /^[-*]\s/.test(l) || l === "")) {
          const items = lines.filter((l) => /^[-*]\s/.test(l));
          return (
            <ul key={bi} className="list-disc list-inside space-y-1">
              {items.map((item, ii) => (
                <li key={ii} className="text-sm text-slate-800 leading-relaxed">
                  {renderInline(item.replace(/^[-*]\s+/, ""))}
                </li>
              ))}
            </ul>
          );
        }

        // Numbered list: lines starting with 1. 2. etc.
        if (lines.every((l) => /^\d+\.\s/.test(l) || l === "")) {
          const items = lines.filter((l) => /^\d+\.\s/.test(l));
          return (
            <ol key={bi} className="list-decimal list-inside space-y-1">
              {items.map((item, ii) => (
                <li key={ii} className="text-sm text-slate-800 leading-relaxed">
                  {renderInline(item.replace(/^\d+\.\s+/, ""))}
                </li>
              ))}
            </ol>
          );
        }

        // Mixed block or paragraph — render each line
        return (
          <p key={bi} className="text-sm text-slate-800 leading-relaxed">
            {lines.map((line, li) => (
              <span key={li}>
                {renderInline(line)}
                {li < lines.length - 1 && <br />}
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}

/** Render inline markdown: **bold**, *italic*, `code` */
function renderInline(text) {
  // Split on bold, italic, and inline-code markers
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-slate-900">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={i}
          className="bg-slate-200 text-slate-800 px-1 rounded text-xs font-mono"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

const MODEL_OPTIONS = [
  { value: "gemini-3-flash-preview", label: "Gemini 3 Flash" },
  { value: "llama-3.3-70b-versatile", label: "Llama 3.3 70B" },
  { value: "llama-3.1-8b-instant", label: "Llama 3.1 8B (fast)" },
];

/** Compact model picker used in both panel and fullscreen headers */
function ModelPicker({ model, onModelChange }) {
  const selectedModel =
    MODEL_OPTIONS.find((option) => option.value === model) || MODEL_OPTIONS[0];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        type="button"
        className="h-7 px-2 sm:px-2.5 rounded-md border border-slate-200 bg-slate-50 text-[11px] sm:text-xs font-medium text-slate-600 focus:outline-none focus:ring-1 focus:ring-blue-400 cursor-pointer inline-flex items-center justify-between gap-1 sm:gap-1.5 min-w-[110px] sm:min-w-[150px]"
        aria-label="Select AI model for follow-up"
      >
        <span className="truncate">{selectedModel.label}</span>
        <FiChevronDown className="w-3 h-3 text-slate-500" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" sideOffset={6} className="w-56">
        {MODEL_OPTIONS.map((option) => (
          <DropdownMenuItem
            key={option.value}
            onClick={() => onModelChange(option.value)}
            className="cursor-pointer flex items-center justify-between"
          >
            <span>{option.label}</span>
            {model === option.value && <FiCheck className="w-3.5 h-3.5" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** Animated "thinking" bubble shown while waiting for the LLM response */
function ThinkingBubble() {
  return (
    <div className="flex justify-start">
      <div className="bg-slate-100 text-slate-500 rounded-2xl px-5 py-3 text-sm flex items-center gap-1">
        <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:0ms]" />
        <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:150ms]" />
        <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:300ms]" />
      </div>
    </div>
  );
}

export default function FollowUpChat({
  messages,
  onSend,
  loading,
  model,
  onModelChange,
}) {
  const [input, setInput] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-open when a new message arrives
  useEffect(() => {
    if (messages.length > 0) setIsOpen(true);
  }, [messages.length]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput("");
  };

  const handleClose = () => {
    setIsFullscreen(false);
    setIsOpen(false);
  };

  const handleCollapse = () => {
    setIsFullscreen(false);
    setIsOpen(false);
  };

  // ── Fullscreen overlay ──────────────────────────────────────────────────────
  if (isFullscreen) {
    return createPortal(
      <div className="fixed inset-0 z-[9999] flex flex-col bg-white">
        {/* Header */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-slate-200 bg-white shadow-sm">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="flex items-center gap-2 text-slate-700 font-semibold text-sm sm:text-base">
              <FiMessageCircle className="w-4 h-4 sm:w-5 sm:h-5 text-blue-600" />
              <span className="hidden sm:inline">Follow-up Chat</span>
              <span className="sm:hidden">Chat</span>
            </div>
            <ModelPicker model={model} onModelChange={onModelChange} />
          </div>
          <button
            onClick={handleClose}
            className="p-2 rounded-full hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition-colors"
            aria-label="Close chat"
          >
            <FiX className="w-5 h-5" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 space-y-4">
          {messages.length === 0 ? (
            <p className="text-center text-slate-400 mt-16 text-sm">
              Ask anything about the search results above.
            </p>
          ) : (
            messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] sm:max-w-[70%] rounded-2xl px-4 sm:px-5 py-3 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-slate-100 text-slate-800"
                  }`}
                >
                  {msg.role === "user" ? (
                    msg.content
                  ) : (
                    <FormattedMessage content={msg.content} />
                  )}
                </div>
              </div>
            ))
          )}
          {loading && <ThinkingBubble />}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="px-3 sm:px-6 py-3 sm:py-4 border-t border-slate-200 bg-white">
          <form
            onSubmit={handleSubmit}
            className="flex items-center gap-2 sm:gap-3"
          >
            <div className="flex items-center flex-grow h-11 sm:h-12 rounded-xl border border-slate-200 bg-slate-50 shadow-sm overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition-all min-w-0">
              <div className="pl-3 sm:pl-4 text-slate-400">
                <FiMessageCircle className="w-4 h-4" />
              </div>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder='e.g., "Why is Product A better than Product C?"'
                className="flex-grow h-full px-2 sm:px-3 bg-transparent text-sm text-slate-900 placeholder-slate-400 focus:outline-none min-w-0"
                aria-label="Follow-up question"
                disabled={loading}
                autoFocus
              />
            </div>
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="h-11 sm:h-12 px-3 sm:px-6 bg-blue-600 text-white rounded-xl font-medium text-sm hover:bg-blue-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 sm:gap-2 flex-shrink-0"
              aria-label="Send follow-up"
            >
              <FiSend className="w-4 h-4" />
              <span className="hidden sm:inline">Send</span>
            </button>
          </form>
        </div>
      </div>,
      document.body,
    );
  }

  // ── Collapsed tab ───────────────────────────────────────────────────────────
  if (!isOpen) {
    return (
      <div className="sticky bottom-0 z-40 flex justify-center pb-3 sm:pb-4 pointer-events-none">
        <button
          onClick={() => setIsOpen(true)}
          className="pointer-events-auto flex items-center gap-2 px-4 sm:px-5 py-2.5 sm:py-3 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 active:scale-95 transition-all duration-200 text-xs sm:text-sm font-medium"
          aria-label="Open follow-up chat"
        >
          <FiMessageCircle className="w-4 h-4" />
          <span className="hidden sm:inline">Follow-up Chat</span>
          <span className="sm:hidden">Chat</span>
          {messages.length > 0 && (
            <span className="ml-1 bg-white text-blue-600 text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
              {messages.length}
            </span>
          )}
        </button>
      </div>
    );
  }

  // ── Expanded panel (sticky bottom) ─────────────────────────────────────────
  return (
    <div className="sticky bottom-0 z-40 bg-white/95 backdrop-blur-md border-t border-slate-200 shadow-xl">
      {/* Panel header */}
      <div className="max-w-3xl mx-auto px-3 sm:px-4 pt-2.5 sm:pt-3 pb-1 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 sm:gap-2.5 min-w-0">
          <div className="flex items-center gap-2 text-slate-600 text-xs sm:text-sm font-medium shrink-0">
            <FiMessageCircle className="w-4 h-4 text-blue-600" />
            <span className="hidden sm:inline">Follow-up Chat</span>
            <span className="sm:hidden">Chat</span>
          </div>
          <ModelPicker model={model} onModelChange={onModelChange} />
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsFullscreen(true)}
            className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
            aria-label="Expand to fullscreen"
            title="Fullscreen"
          >
            <FiMaximize2 className="w-4 h-4" />
          </button>
          <button
            onClick={handleCollapse}
            className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
            aria-label="Collapse chat"
            title="Collapse"
          >
            <FiChevronDown className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Chat messages */}
      <div className="max-w-3xl mx-auto px-3 sm:px-4 pt-2 pb-2 max-h-56 sm:max-h-60 overflow-y-auto space-y-2.5 sm:space-y-3">
        {messages.length === 0 ? (
          <p className="text-center text-slate-400 text-xs py-2">
            Ask anything about the search results above.
          </p>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] sm:max-w-[80%] rounded-lg px-3 sm:px-4 py-2 text-xs sm:text-sm ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-800"
                }`}
              >
                {msg.role === "user" ? (
                  msg.content
                ) : (
                  <FormattedMessage content={msg.content} />
                )}
              </div>
            </div>
          ))
        )}
        {loading && <ThinkingBubble />}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="max-w-3xl mx-auto px-3 sm:px-4 py-2.5 sm:py-3">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <div className="flex items-center flex-grow h-11 sm:h-12 rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition-all min-w-0">
            <div className="pl-3 text-slate-400">
              <FiMessageCircle className="w-4 h-4" />
            </div>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder='e.g., "Why is Product A better than Product C?"'
              className="flex-grow h-full px-2 sm:px-3 bg-transparent text-sm text-slate-900 placeholder-slate-400 focus:outline-none min-w-0"
              aria-label="Follow-up question"
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="h-11 sm:h-12 px-3 sm:px-5 bg-blue-600 text-white rounded-lg font-medium text-sm hover:bg-blue-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 flex-shrink-0"
            aria-label="Send follow-up"
          >
            <FiSend className="w-4 h-4" />
            <span className="hidden sm:inline">Send</span>
          </button>
        </form>
      </div>
    </div>
  );
}
