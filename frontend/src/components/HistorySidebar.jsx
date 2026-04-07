/**
 * HistorySidebar — full-height slide-in panel showing past searches.
 *
 * Opens/closes via HistoryContext.sidebarOpen.
 * Clicking an entry re-runs that query via the onHistoryClick prop.
 * Individual entries can be removed; the trash icon in the header clears all.
 */
import { motion, AnimatePresence } from "motion/react";
import { Clock, Trash2, X, ShoppingBag } from "lucide-react";
import { useHistory } from "../contexts/HistoryContext";
import { useCurrency } from "../contexts/CurrencyContext";
import { useSearch } from "../contexts/SearchContext";

function formatRelativeDate(timestamp) {
  const diffMs = Date.now() - timestamp;
  const diffH = diffMs / (1000 * 60 * 60);
  if (diffH < 1) return "Just now";
  if (diffH < 24) return `${Math.floor(diffH)}h ago`;
  if (diffH < 48) return "Yesterday";
  return new Date(timestamp).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export default function HistorySidebar({ onHistoryClick }) {
  const { history, sidebarOpen, setSidebarOpen, deleteEntry, clearHistory } =
    useHistory();
  const {
    displayCurrency,
    setDisplayCurrency,
    switchCurrency,
    exchangeRate,
    switching,
  } = useCurrency();
  const { threadId, updateProducts } = useSearch();

  const handleCurrencyToggle = async (currency) => {
    if (currency === displayCurrency || switching) return;
    if (threadId) {
      const result = await switchCurrency(threadId, currency);
      if (result) {
        updateProducts(result.ranked_products, result.excluded_products);
      }
    } else {
      setDisplayCurrency(currency);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            key="sidebar-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40 bg-black/20 backdrop-blur-[2px]"
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar panel */}
      <motion.aside
        initial={false}
        animate={{ x: sidebarOpen ? 0 : "-100%" }}
        transition={{ type: "spring", stiffness: 340, damping: 34 }}
        className="fixed top-0 left-0 h-screen w-[86vw] max-w-72 sm:w-72 z-50 flex flex-col bg-white/95 backdrop-blur-md border-r border-slate-200 shadow-2xl"
        aria-label="Search history"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3.5 border-b border-slate-200 bg-slate-50/80 flex-shrink-0">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-purple-600" />
            <span className="font-semibold text-slate-800 text-sm font-lexend">
              Search History
            </span>
            {history.length > 0 && (
              <span className="text-xs bg-purple-100 text-purple-600 font-medium px-1.5 py-0.5 rounded-full">
                {history.length}
              </span>
            )}
          </div>

          <div className="flex items-center gap-0.5">
            {/* Clear all */}
            {history.length > 0 && (
              <button
                onClick={clearHistory}
                title="Clear all history"
                className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                aria-label="Clear all history"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
            {/* Close */}
            <button
              onClick={() => setSidebarOpen(false)}
              className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded-lg transition-colors"
              aria-label="Close history sidebar"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Currency switcher — visible on mobile only */}
        <div className="sm:hidden px-4 py-3 border-b border-slate-200 bg-slate-50/50">
          <p className="text-xs font-medium text-slate-500 mb-2">Currency</p>
          <div className="flex items-center bg-slate-100 rounded-full p-0.5">
            <button
              onClick={() => handleCurrencyToggle("PKR")}
              className={`flex-1 px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
                displayCurrency === "PKR"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
              disabled={switching}
            >
              PKR
            </button>
            <button
              onClick={() => handleCurrencyToggle("USD")}
              className={`flex-1 px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
                displayCurrency === "USD"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
              disabled={switching}
            >
              USD
            </button>
          </div>
          <p className="text-[10px] text-slate-400 mt-1.5 text-center">
            1 USD = {exchangeRate.usd_to_pkr?.toFixed(2)} PKR
          </p>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto py-2 min-h-0">
          {history.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-3 px-6 text-center">
              <ShoppingBag className="w-10 h-10 text-slate-300" />
              <p className="text-slate-400 text-sm font-medium">
                No searches yet
              </p>
              <p className="text-slate-300 text-xs leading-relaxed">
                Your searches will appear here and are kept for 7 days.
              </p>
            </div>
          ) : (
            <ul className="px-2 space-y-0.5">
              {history.map((entry) => (
                <li key={entry.id} className="group relative">
                  <button
                    className="w-full text-left px-3 py-3 pr-8 rounded-xl hover:bg-purple-50 transition-colors"
                    onClick={() => {
                      onHistoryClick(entry);
                      setSidebarOpen(false);
                    }}
                    title={entry.query}
                  >
                    <p className="text-sm text-slate-700 font-medium leading-snug line-clamp-2">
                      {entry.query}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-slate-400">
                        {formatRelativeDate(entry.timestamp)}
                      </span>
                      {entry.productCount > 0 && (
                        <span className="text-xs text-purple-500 font-medium">
                          {entry.productCount} product
                          {entry.productCount !== 1 ? "s" : ""}
                        </span>
                      )}
                      <span className="text-xs text-slate-300">
                        {entry.currency}
                      </span>
                    </div>
                  </button>

                  {/* Per-entry delete — shown on hover */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteEntry(entry.id);
                    }}
                    title="Remove"
                    aria-label="Remove this entry"
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Footer */}
        {history.length > 0 && (
          <div className="px-4 py-2.5 border-t border-slate-100 flex-shrink-0">
            <p className="text-xs text-slate-400 text-center">
              {history.length} search{history.length !== 1 ? "es" : ""} &middot;
              expires after 7 days
            </p>
          </div>
        )}
      </motion.aside>
    </>
  );
}
