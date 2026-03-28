/**
 * ReviewInsights — displays review sentiment, themes, and summaries for top products.
 */
export default function ReviewInsights({ products }) {
  // Only show products that have review data
  const withReviews = products?.filter((p) => p.review_sentiment != null) || [];
  if (!withReviews.length) return null;

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold font-lexend text-slate-900">
        💬 Review Analysis
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {withReviews.slice(0, 3).map((product) => {
          const sentimentPct = Math.round((product.review_sentiment || 0) * 100);

          return (
            <div
              key={product.id}
              className="bg-white rounded-xl shadow-md p-5 space-y-4 hover:shadow-lg transition-all duration-200"
            >
              {/* Product name */}
              <h3 className="text-sm font-semibold font-lexend text-slate-900 line-clamp-1">
                {product.name}
              </h3>

              {/* Sentiment bar */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-slate-500">Sentiment</span>
                  <span className="text-emerald-600">{sentimentPct}% positive</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-3">
                  <div
                    className="bg-emerald-500 h-3 rounded-full transition-all duration-500"
                    style={{ width: `${sentimentPct}%` }}
                  />
                </div>
              </div>

              {/* Positive themes */}
              {product.review_positive_themes?.length > 0 && (
                <div className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                    Positive
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {product.review_positive_themes.map((theme, i) => (
                      <span
                        key={i}
                        className="bg-emerald-50 text-emerald-700 text-xs rounded-full px-2.5 py-0.5"
                      >
                        {theme}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Negative themes */}
              {product.review_negative_themes?.length > 0 && (
                <div className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
                    Negative
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {product.review_negative_themes.map((theme, i) => (
                      <span
                        key={i}
                        className="bg-red-50 text-red-700 text-xs rounded-full px-2.5 py-0.5"
                      >
                        {theme}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Review summary */}
              {product.review_summary && (
                <p className="text-sm text-slate-500 italic leading-relaxed">
                  {product.review_summary}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
