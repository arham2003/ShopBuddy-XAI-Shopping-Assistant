/**
 * HeroSearch — large centered search input with model selector, keyword confirmation, and suggestion chips.
 */
import { useState } from "react";
import { FiSearch } from "react-icons/fi";
import { TypingAnimation } from "@/components/ui/typing-animation";
import { ShimmerButton } from "@/components/ui/shimmer-button";

const SUGGESTIONS = [
  "Juicer Blender",
  "Wireless Earbuds",
  "Running Shoes",
  "Laptop Stand",
];

export default function HeroSearch({ onSearch, onConfirm, onEdit, interrupt }) {
  const [input, setInput] = useState("");
  const [model, setModel] = useState("gemini-3-flash-preview");
  const [editingKeywords, setEditingKeywords] = useState(false);
  const [editedKeywords, setEditedKeywords] = useState("");

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
    <div className="text-center py-12 space-y-6">
      <TypingAnimation
        as="h1"
        className="text-3xl font-bold font-lexend text-slate-900"
        duration={55}
      >
        What are you shopping for today?
      </TypingAnimation>
      <p className="text-slate-500 text-sm max-w-2xl mx-auto">
        We search and compare Daraz.pk &amp; Amazon, explain every
        recommendation, and show you what the AI filtered out.
      </p>

      {/* Search bar */}
      <form
        onSubmit={handleSubmit}
        className="max-w-3xl mx-auto flex flex-col sm:flex-row items-stretch gap-3"
      >
        <div className="flex-1 flex items-center h-14 text-lg rounded-xl shadow-sm border border-slate-200 overflow-hidden bg-white focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition-all">
          <div className="pl-4 text-slate-400">
            <FiSearch className="w-5 h-5" />
          </div>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="e.g., best juicer blender under 5000 PKR"
            className="flex-grow h-full px-3 bg-transparent text-slate-900 placeholder-slate-400 focus:outline-none text-base font-inter"
            aria-label="Search products"
          />
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="h-10 mx-2 px-3 min-w-[145px] rounded-md border border-slate-300 bg-slate-50 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
            aria-label="Select AI model"
          >
            <option value="gemini-3-flash-preview">Gemini 3 Flash</option>
            <option value="llama-3.3-70b-versatile">Llama 3.3 70B</option>
            <option value="llama-3.1-8b-instant">Llama 3.1 8B</option>
          </select>
        </div>
        <ShimmerButton
          type="submit"
          aria-label="Search"
          background="#2563eb"
          shimmerColor="#c7d2fe"
          className="h-14 min-w-[130px] rounded-xl text-sm sm:text-base font-semibold"
        >
          <span className="relative z-10">Search</span>
        </ShimmerButton>
      </form>

      {/* Keyword confirmation step */}
      {interrupt && !editingKeywords && (
        <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-md border border-slate-200 p-5 space-y-4">
          <p className="text-sm text-slate-700">
            <span className="mr-1">🔍</span>
            AI extracted keywords:{" "}
            {interrupt.search_terms?.map((kw, i) => (
              <span
                key={i}
                className="inline-block bg-indigo-50 text-indigo-700 rounded-full px-3 py-0.5 text-sm font-medium mx-1"
              >
                {kw}
              </span>
            ))}
            {interrupt.budget_max && (
              <span className="text-slate-500 ml-2">
                Budget: {interrupt.budget_currency === "USD" ? "$" : "Rs. "}
                {interrupt.budget_max?.toLocaleString()}
              </span>
            )}
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={handleConfirm}
              className="flex items-center gap-1.5 px-5 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-all duration-200"
              aria-label="Confirm keywords and search"
            >
              ✅ Confirm &amp; Search
            </button>
            <button
              onClick={handleStartEdit}
              className="flex items-center gap-1.5 px-5 py-2 bg-slate-100 text-slate-700 font-medium rounded-lg hover:bg-slate-200 transition-all duration-200"
              aria-label="Edit keywords"
            >
              ✏️ Edit Keywords
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
