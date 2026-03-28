/**
 * ProductCard — displays a single product with pricing, rating, badge, and explainability.
 * Memoized with React.memo to prevent unnecessary re-renders.
 */
import { memo } from 'react';
import { FiExternalLink, FiStar } from 'react-icons/fi';
import { useCurrency } from '../contexts/CurrencyContext';
import PlatformBadge from './PlatformBadge';
import ExplainabilityPanel from './ExplainabilityPanel';

const BADGE_STYLES = {
  'Best Overall': 'bg-blue-600 text-white',
  'Best Value': 'bg-emerald-600 text-white',
  'Best Rated': 'bg-amber-500 text-white',
  'Top Rated': 'bg-amber-500 text-white',
};

function ProductCard({ product, badge }) {
  const { displayCurrency, formatPrice, switching } = useCurrency();

  const {
    name, brand, source, image_url, product_url,
    price_display, currency_display,
    price_original, currency_original,
    rating, review_count,
    reasoning_chain, value_score, cross_platform_note,
  } = product;

  // Determine primary and secondary price display
  const primaryPrice = formatPrice(price_display, currency_display || displayCurrency);
  const showSecondary = currency_original && currency_display !== currency_original;
  const secondaryPrice = showSecondary
    ? `(${formatPrice(price_original, currency_original)} ${currency_original})`
    : null;

  // Top badge (Best Overall, Best Value, etc.)
  const topBadge = badge || product.recommendation_badge;
  const badgeClass = topBadge ? (BADGE_STYLES[topBadge] || 'bg-slate-600 text-white') : null;

  return (
    <div className="bg-white rounded-xl shadow-md hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 overflow-hidden flex flex-col">
      {/* Top badge */}
      {topBadge && (
        <div className={`${badgeClass} text-sm font-semibold px-4 py-1.5 text-center`}>
          {topBadge === 'Best Overall' && '🏆 '}
          {topBadge === 'Best Value' && '💰 '}
          {(topBadge === 'Best Rated' || topBadge === 'Top Rated') && '⭐ '}
          {topBadge}
        </div>
      )}

      <div className="p-5 flex flex-col flex-grow">
        {/* Product image */}
        <div className="bg-slate-50 rounded-lg h-48 flex items-center justify-center mb-4 overflow-hidden">
          {image_url ? (
            <img
              src={image_url}
              alt={name}
              className="h-full w-full object-contain"
              loading="lazy"
            />
          ) : (
            <div className="text-slate-300 text-4xl">📦</div>
          )}
        </div>

        {/* Platform badge */}
        <div className="mb-2">
          <PlatformBadge source={source} />
        </div>

        {/* Product name */}
        <h3 className="text-lg font-semibold font-lexend text-slate-900 line-clamp-2 mb-1">
          {name}
        </h3>

        {/* Brand */}
        {brand && (
          <p className="text-sm text-slate-400 mb-3">{brand}</p>
        )}

        {/* Price */}
        <div className={`mb-3 ${switching ? 'opacity-50 animate-pulse' : ''}`}>
          <p className="text-2xl font-bold font-lexend text-slate-900">{primaryPrice}</p>
          {secondaryPrice && (
            <p className="text-sm text-slate-400">{secondaryPrice}</p>
          )}
        </div>

        {/* Rating */}
        <div className="flex items-center gap-2 text-sm text-slate-600 mb-3">
          <FiStar className="w-4 h-4 text-amber-500 fill-amber-500" />
          <span className="font-medium">{rating?.toFixed(1) || 'N/A'}</span>
          <span className="text-slate-400">•</span>
          <span className="text-slate-400">{review_count?.toLocaleString() || 0} reviews</span>
        </div>

        {/* Explainability panel */}
        <ExplainabilityPanel
          reasoningChain={reasoning_chain}
          confidenceScore={value_score}
          crossPlatformNote={cross_platform_note}
        />

        {/* View on platform link */}
        <div className="mt-auto pt-4">
          <a
            href={product_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 underline-offset-2 transition-colors"
            aria-label={`View ${name} on ${source}`}
          >
            View on {source === 'daraz' ? 'Daraz' : 'Amazon'}
            <FiExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
}

export default memo(ProductCard);
