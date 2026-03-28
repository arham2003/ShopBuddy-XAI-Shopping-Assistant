/**
 * Navbar — sticky top bar with app title and currency toggle.
 */
import { useCurrency } from '../contexts/CurrencyContext';
import { useSearch } from '../contexts/SearchContext';

export default function Navbar() {
  const { displayCurrency, setDisplayCurrency, switchCurrency, exchangeRate, switching } = useCurrency();
  const { threadId, updateProducts } = useSearch();

  const handleToggle = async (currency) => {
    if (currency === displayCurrency || switching) return;

    // If we have an active session, call the backend to re-convert prices
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
    <nav className="bg-white/80 backdrop-blur-md shadow-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
        {/* Logo */}
        <div className="font-lexend text-xl font-bold text-slate-900 flex items-center gap-2">
          <span>🛒</span>
          <span>Shop<span className="text-purple-600">Buddy</span></span>
        </div>

        {/* Currency toggle */}
        <div className="flex flex-col items-end gap-1">
          <div className="flex items-center bg-slate-100 rounded-full p-0.5">
            <button
              onClick={() => handleToggle('PKR')}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
                displayCurrency === 'PKR'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              aria-label="Switch to Pakistani Rupees"
              disabled={switching}
            >
              🇵🇰 PKR
            </button>
            <button
              onClick={() => handleToggle('USD')}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
                displayCurrency === 'USD'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              aria-label="Switch to US Dollars"
              disabled={switching}
            >
              🇺🇸 USD
            </button>
          </div>
          <span className="text-xs text-slate-400">
            1 USD = {exchangeRate.usd_to_pkr?.toFixed(2)} PKR • Rates By ExchangeRate-API
          </span>
        </div>
      </div>
    </nav>
  );
}
