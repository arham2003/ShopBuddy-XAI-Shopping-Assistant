/**
 * SecondChanceShelf — shows excluded products grouped by filter reason.
 */
import { useMemo } from 'react';
import { FiExternalLink } from 'react-icons/fi';
import { useCurrency } from '../contexts/CurrencyContext';
import PlatformBadge from './PlatformBadge';

// Keys match the filter_name values emitted by filter_agent.py
const REASON_GROUPS = {
  budget: { label: '💰 Over Budget', icon: '💰' },
  minimum_reviews: { label: '💬 Too Few Reviews', icon: '💬' },
  relevance: { label: '🎯 Not Relevant to Search', icon: '🎯' },
  duplicate: { label: '🔄 Duplicate Listing', icon: '🔄' },
};

// Display order — budget & reviews first, then relevance, then duplicates
const GROUP_ORDER = ['budget', 'minimum_reviews', 'relevance', 'duplicate'];

export default function SecondChanceShelf({ products }) {
  const { formatPrice, displayCurrency } = useCurrency();

  // Group by filter_name, max 5 per group, ordered by GROUP_ORDER
  const groups = useMemo(() => {
    if (!products?.length) return {};
    const map = {};
    for (const p of products) {
      const key = p.filter_name || 'other';
      if (!map[key]) map[key] = [];
      if (map[key].length < 5) map[key].push(p);
    }
    // Sort keys by preferred order, unknown keys at the end
    const sorted = {};
    for (const k of GROUP_ORDER) {
      if (map[k]) sorted[k] = map[k];
    }
    for (const k of Object.keys(map)) {
      if (!sorted[k]) sorted[k] = map[k];
    }
    return sorted;
  }, [products]);

  if (!Object.keys(groups).length) return null;

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold font-lexend text-slate-900">
          🔄 Products That Almost Made It
        </h2>
        <p className="text-sm text-slate-500 mt-1">
          These products were filtered out but might still interest you.
        </p>
      </div>

      <div className="space-y-6">
        {Object.entries(groups).map(([key, items]) => {
          const group = REASON_GROUPS[key] || { label: `🔍 Other (${key})`, icon: '🔍' };
          return (
            <div key={key} className="space-y-2">
              <h3 className="text-sm font-semibold font-lexend text-slate-700">
                {group.label}
              </h3>
              <div className="space-y-2">
                {items.map((p) => (
                  <div
                    key={p.id}
                    className="bg-white rounded-lg shadow-sm border border-slate-100 p-4 flex items-center justify-between gap-4"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <PlatformBadge source={p.source} />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-slate-900 truncate">
                          {p.name}
                        </p>
                        <p className="text-red-600 text-xs mt-0.5">
                          {p.filter_reason || `Excluded by ${key} filter`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 flex-shrink-0">
                      <span className="text-base font-semibold font-inter text-slate-900">
                        {formatPrice(p.price_display, p.currency_display || displayCurrency)}
                      </span>
                      <a
                        href={p.product_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 hover:text-blue-700 whitespace-nowrap flex items-center gap-1"
                        aria-label={`View ${p.name}`}
                      >
                        View anyway <FiExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
