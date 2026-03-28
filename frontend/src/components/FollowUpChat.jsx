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
} from "react-icons/fi";

export default function FollowUpChat({ messages, onSend, loading }) {
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
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-white shadow-sm">
          <div className="flex items-center gap-2 text-slate-700 font-semibold">
            <FiMessageCircle className="w-5 h-5 text-blue-600" />
            Follow-up Chat
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
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
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
                  className={`max-w-[70%] rounded-2xl px-5 py-3 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-slate-100 text-slate-800"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="px-6 py-4 border-t border-slate-200 bg-white">
          <form onSubmit={handleSubmit} className="flex items-center gap-3">
            <div className="flex items-center flex-grow h-12 rounded-xl border border-slate-200 bg-slate-50 shadow-sm overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition-all">
              <div className="pl-4 text-slate-400">
                <FiMessageCircle className="w-4 h-4" />
              </div>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder='e.g., "Why is Product A better than Product C?"'
                className="flex-grow h-full px-3 bg-transparent text-sm text-slate-900 placeholder-slate-400 focus:outline-none"
                aria-label="Follow-up question"
                disabled={loading}
                autoFocus
              />
            </div>
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="h-12 px-6 bg-blue-600 text-white rounded-xl font-medium text-sm hover:bg-blue-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              aria-label="Send follow-up"
            >
              <FiSend className="w-4 h-4" />
              Send
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
      <div className="sticky bottom-0 z-40 flex justify-center pb-4 pointer-events-none">
        <button
          onClick={() => setIsOpen(true)}
          className="pointer-events-auto flex items-center gap-2 px-5 py-3 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 active:scale-95 transition-all duration-200 text-sm font-medium"
          aria-label="Open follow-up chat"
        >
          <FiMessageCircle className="w-4 h-4" />
          Follow-up Chat
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
      <div className="max-w-3xl mx-auto px-4 pt-3 pb-1 flex items-center justify-between">
        <div className="flex items-center gap-2 text-slate-600 text-sm font-medium">
          <FiMessageCircle className="w-4 h-4 text-blue-600" />
          Follow-up Chat
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
      <div className="max-w-3xl mx-auto px-4 pt-2 pb-2 max-h-60 overflow-y-auto space-y-3">
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
                className={`max-w-[80%] rounded-lg px-4 py-2 text-sm ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-800"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="max-w-3xl mx-auto px-4 py-3">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <div className="flex items-center flex-grow h-12 rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition-all">
            <div className="pl-3 text-slate-400">
              <FiMessageCircle className="w-4 h-4" />
            </div>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder='e.g., "Why is Product A better than Product C?"'
              className="flex-grow h-full px-3 bg-transparent text-sm text-slate-900 placeholder-slate-400 focus:outline-none"
              aria-label="Follow-up question"
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="h-12 px-5 bg-blue-600 text-white rounded-lg font-medium text-sm hover:bg-blue-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
            aria-label="Send follow-up"
          >
            <FiSend className="w-4 h-4" />
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
