/**
 * HeroSearch — large centered search input with model selector, keyword confirmation, and suggestion chips.
 */
import { useState } from "react";
import { FiSearch, FiChevronDown, FiCheck } from "react-icons/fi";
import { TypingAnimation } from "@/components/ui/typing-animation";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const SUGGESTIONS = [
  "Juicer Blender",
  "Wireless Earbuds",
  "Running Shoes",
  "Laptop Stand",
];

const MODEL_OPTIONS = [
  { value: "gemini-3-flash-preview", label: "Gemini 3 Flash" },
  { value: "llama-3.3-70b-versatile", label: "Llama 3.3 70B" },
  { value: "llama-3.1-8b-instant", label: "Llama 3.1 8B" },
];

export default function HeroSearch({ onSearch, onConfirm, onEdit, interrupt }) {
  const [input, setInput] = useState("");
  const [model, setModel] = useState("gemini-3-flash-preview");
  const [editingKeywords, setEditingKeywords] = useState(false);
  const [editedKeywords, setEditedKeywords] = useState("");
  const isSearchDisabled = !input.trim();
  const selectedModel =
    MODEL_OPTIONS.find((option) => option.value === model) || MODEL_OPTIONS[0];

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    onSearch(input.trim(), model);
  };

  const handleChip = (text) => {
    setInput(text);
    onSearch(text, model);
  };

  // Keyword confirmation UI
  const handleConfirm = () => {
    onConfirm();
  };

  const handleStartEdit = () => {
    setEditingKeywords(true);
    setEditedKeywords(interrupt?.search_terms?.join(", ") || "");
  };

  const handleEditSubmit = () => {
    setEditingKeywords(false);
    onEdit(editedKeywords);
  };

  return (
    <div className="text-center py-8 sm:py-12 space-y-4 sm:space-y-6 px-1">
      <TypingAnimation
        as="h1"
        className="text-2xl sm:text-4xl font-semibold text-slate-900"
        style={{ fontFamily: '"Libre Bodoni", serif', fontStyle: "italic" }}
        duration={55}
      >
        What are you shopping for today?
      </TypingAnimation>
      <p className="text-slate-500 text-xs sm:text-sm max-w-3xl mx-auto">
        We search and compare Daraz.pk &amp; Amazon, explain every
        recommendation,<br className="hidden sm:inline" /> and show you what the AI filtered out.
      </p>

      {/* Search bar */}
      <form
        onSubmit={handleSubmit}
        className="max-w-3xl mx-auto flex flex-col sm:flex-row items-stretch gap-2 sm:gap-3"
      >
        <div className="flex-1 flex items-center h-12 sm:h-14 rounded-xl shadow-sm border border-slate-200 overflow-hidden bg-white focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition-all">
          <div className="pl-3 sm:pl-4 text-slate-400">
            <FiSearch className="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="e.g., best juicer blender under 5000 PKR"
            className="flex-grow h-full px-2 sm:px-3 bg-transparent text-slate-900 placeholder-slate-400 focus:outline-none text-sm sm:text-base min-w-0"
            aria-label="Search products"
          />
          <DropdownMenu>
            <DropdownMenuTrigger
              type="button"
              className="h-8 sm:h-10 mx-1.5 sm:mx-2 px-2 sm:px-3 min-w-[100px] sm:min-w-[140px] rounded-md border border-slate-300 bg-slate-50 text-[11px] sm:text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer inline-flex items-center justify-between gap-1 sm:gap-2 flex-shrink-0"
              aria-label="Select AI model"
            >
              <span className="truncate">{selectedModel.label}</span>
              <FiChevronDown className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-slate-500" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" sideOffset={8} className="w-48 sm:w-56">
              {MODEL_OPTIONS.map((option) => (
                <DropdownMenuItem
                  key={option.value}
                  onClick={() => setModel(option.value)}
                  className="cursor-pointer flex items-center justify-between text-sm"
                >
                  <span>{option.label}</span>
                  {model === option.value && (
                    <FiCheck className="w-3.5 h-3.5" />
                  )}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <ShimmerButton
          type="submit"
          disabled={isSearchDisabled}
          aria-label="Search"
          background="#2563eb"
          shimmerColor="#c7d2fe"
          className="h-12 sm:h-14 w-auto sm:min-w-[130px] self-center sm:self-stretch px-8 sm:px-0 rounded-xl text-sm sm:text-base font-semibold disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:brightness-100 disabled:hover:translate-y-0"
        >
          <span className="relative z-10">Search</span>
        </ShimmerButton>
      </form>

      {/* Keyword confirmation step */}
      {interrupt && !editingKeywords && (
        <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-md border border-slate-200 p-4 sm:p-5 space-y-3 sm:space-y-4">
          <p className="text-xs sm:text-sm text-slate-700">
            <span className="mr-1">🔍</span>
            AI extracted keywords:{" "}
            {interrupt.search_terms?.map((kw, i) => (
              <span
                key={i}
                className="inline-block bg-indigo-50 text-indigo-700 rounded-full px-2 sm:px-3 py-0.5 text-xs sm:text-sm font-medium mx-0.5 sm:mx-1 mt-1"
              >
                {kw}
              </span>
            ))}
            {interrupt.budget_max && (
              <span className="text-slate-500 ml-1 sm:ml-2 text-xs sm:text-sm">
                Budget: {interrupt.budget_currency === "USD" ? "$" : "Rs. "}
                {interrupt.budget_max?.toLocaleString()}
              </span>
            )}
          </p>
          <div className="flex items-center justify-center gap-2 sm:gap-3">
            <button
              onClick={handleConfirm}
              className="flex items-center gap-1.5 px-4 sm:px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-all duration-200"
              aria-label="Confirm keywords and search"
            >
              Confirm &amp; Search
            </button>
            <button
              onClick={handleStartEdit}
              className="flex items-center gap-1.5 px-4 sm:px-5 py-2 bg-slate-100 text-slate-700 text-sm font-medium rounded-lg hover:bg-slate-200 transition-all duration-200"
              aria-label="Edit keywords"
            >
              Edit Keywords
            </button>
          </div>
        </div>
      )}

      {/* Editing keywords mode */}
      {interrupt && editingKeywords && (
        <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-md border border-slate-200 p-5 space-y-4">
          <label className="block text-sm font-medium text-slate-700 text-left">
            Edit search keywords:
          </label>
          <input
            type="text"
            value={editedKeywords}
            onChange={(e) => setEditedKeywords(e.target.value)}
            className="w-full h-12 px-4 rounded-lg border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Edit search keywords"
          />
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={handleEditSubmit}
              className="px-5 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-all duration-200"
              aria-label="Search with edited keywords"
            >
              🔍 Search with these
            </button>
            <button
              onClick={() => setEditingKeywords(false)}
              className="px-5 py-2 bg-slate-100 text-slate-700 font-medium rounded-lg hover:bg-slate-200 transition-all duration-200"
              aria-label="Cancel edit"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Suggestion chips */}
      {!interrupt && (
        <div className="flex flex-wrap items-center justify-center gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => handleChip(s)}
              className="bg-slate-100 text-slate-600 rounded-full px-4 py-1.5 text-sm hover:bg-blue-50 hover:text-blue-600 cursor-pointer transition-all duration-200"
              aria-label={`Search for ${s}`}
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
