/**
 * Navbar — sticky top bar with app title and currency toggle.
 * Currency switcher is hidden on mobile (moved to HistorySidebar).
 */
import { useCurrency } from "../contexts/CurrencyContext";
import { useSearch } from "../contexts/SearchContext";
import { useHistory } from "../contexts/HistoryContext";
import { History, Menu } from "lucide-react";

export default function Navbar() {
  const {
    displayCurrency,
    setDisplayCurrency,
    switchCurrency,
    exchangeRate,
    switching,
  } = useCurrency();
  const { threadId, updateProducts } = useSearch();
  const { sidebarOpen, setSidebarOpen, history } = useHistory();

  const handleToggle = async (currency) => {
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
    <nav className="bg-white/80 backdrop-blur-md shadow-sm fixed top-0 inset-x-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-14 sm:h-16">
        {/* Left: sidebar toggle + logo */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Mobile: hamburger menu icon */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="relative p-2 rounded-lg text-slate-500 hover:text-purple-600 hover:bg-purple-50 transition-colors sm:hidden"
            aria-label="Open menu"
            title="Menu"
          >
            <Menu className="w-5 h-5" />
            {history.length > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-purple-600 text-white text-[10px] font-bold rounded-full flex items-center justify-center leading-none">
                {history.length > 9 ? "9+" : history.length}
              </span>
            )}
          </button>

          {/* Desktop: history icon */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="relative p-2 rounded-lg text-slate-500 hover:text-purple-600 hover:bg-purple-50 transition-colors hidden sm:block"
            aria-label="Toggle search history"
            title="Search history"
          >
            <History className="w-5 h-5" />
            {history.length > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-purple-600 text-white text-[10px] font-bold rounded-full flex items-center justify-center leading-none">
                {history.length > 9 ? "9+" : history.length}
              </span>
            )}
          </button>

          <div className="font-lexend text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-1.5 sm:gap-2">
            <span>🛒</span>
            <span>
              Shop<span className="text-blue-700">Buddy</span>
            </span>
          </div>
        </div>

        {/* Currency toggle — hidden on mobile, shown on sm+ */}
        <div className="hidden sm:flex flex-col items-end gap-1">
          <div className="flex items-center bg-slate-100 rounded-full p-0.5">
            <button
              onClick={() => handleToggle("PKR")}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
                displayCurrency === "PKR"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
              aria-label="Switch to Pakistani Rupees"
              disabled={switching}
            >
              PKR
            </button>
            <button
              onClick={() => handleToggle("USD")}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
                displayCurrency === "USD"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
              aria-label="Switch to US Dollars"
              disabled={switching}
            >
              USD
            </button>
          </div>
          <span className="text-xs text-slate-400">
            1 USD = {exchangeRate.usd_to_pkr?.toFixed(2)} PKR
          </span>
        </div>

        {/* Mobile: show current currency indicator */}
        <div className="flex sm:hidden items-center">
          <span className="text-xs font-medium text-slate-500 bg-slate-100 px-2 py-1 rounded-full">
            {displayCurrency}
          </span>
        </div>
      </div>
    </nav>
  );
}
