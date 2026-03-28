/**
 * CurrencyContext — manages display currency, exchange rate, and price formatting.
 */
import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { getExchangeRate, switchCurrency as apiSwitchCurrency } from '../services/api';

const CurrencyContext = createContext(null);

export function CurrencyProvider({ children }) {
  const [displayCurrency, setDisplayCurrencyState] = useState('PKR');
  const [exchangeRate, setExchangeRate] = useState({
    usd_to_pkr: 277.87,
    pkr_to_usd: 0.003599,
    last_updated: '',
    source: 'fallback',
  });
  const [switching, setSwitching] = useState(false);

  // Fetch initial exchange rate on mount
  useEffect(() => {
    getExchangeRate()
      .then(setExchangeRate)
      .catch(() => {}); // keep fallback
  }, []);

  const formatPrice = useCallback(
    (amount, currency) => {
      if (currency === 'PKR') {
        return `Rs. ${Number(amount).toLocaleString('en-PK', { maximumFractionDigits: 0 })}`;
      }
      return `$${Number(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    },
    []
  );

  // Switch currency — calls backend to re-convert prices for a given thread
  const switchCurrency = useCallback(
    async (threadId, newCurrency) => {
      setSwitching(true);
      try {
        const result = await apiSwitchCurrency(threadId, newCurrency);
        setDisplayCurrencyState(newCurrency);
        if (result.exchange_rate) {
          setExchangeRate((prev) => ({ ...prev, ...result.exchange_rate }));
        }
        return result;
      } finally {
        setSwitching(false);
      }
    },
    []
  );

  // Simple toggle without backend call (e.g., before any search)
  const setDisplayCurrency = useCallback((c) => setDisplayCurrencyState(c), []);

  const value = useMemo(
    () => ({
      displayCurrency,
      setDisplayCurrency,
      switchCurrency,
      exchangeRate,
      setExchangeRate,
      formatPrice,
      switching,
    }),
    [displayCurrency, setDisplayCurrency, switchCurrency, exchangeRate, formatPrice, switching]
  );

  return <CurrencyContext.Provider value={value}>{children}</CurrencyContext.Provider>;
}

export function useCurrency() {
  const ctx = useContext(CurrencyContext);
  if (!ctx) throw new Error('useCurrency must be used inside CurrencyProvider');
  return ctx;
}
