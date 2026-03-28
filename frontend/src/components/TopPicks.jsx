/**
 * TopPicks — displays the top 3 recommended products in a grid.
 */
import { useMemo } from 'react';
import ProductCard from './ProductCard';

const BADGE_ORDER = ['Best Overall', 'Best Value', 'Best Rated'];

export default function TopPicks({ products }) {
  // Take top 3 and assign badges
  const topThree = useMemo(() => {
    if (!products?.length) return [];
    return products.slice(0, 3).map((p, i) => ({
      ...p,
      _badge: p.recommendation_badge || BADGE_ORDER[i] || null,
    }));
  }, [products]);

  if (!topThree.length) return null;

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold font-lexend text-slate-900">
        🏆 Top Recommendations
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {topThree.map((product) => (
          <ProductCard
            key={product.id}
            product={product}
            badge={product._badge}
          />
        ))}
      </div>
    </section>
  );
}
