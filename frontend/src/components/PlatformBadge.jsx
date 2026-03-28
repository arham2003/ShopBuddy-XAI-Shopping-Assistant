/**
 * PlatformBadge — displays a colored badge for Daraz or Amazon.
 */
export default function PlatformBadge({ source }) {
  if (source === 'daraz') {
    return (
      <span className="inline-block bg-orange-500 text-white text-xs font-bold px-2.5 py-0.5 rounded-full">
        Daraz
      </span>
    );
  }
  if (source === 'amazon') {
    return (
      <span className="inline-block bg-yellow-400 text-slate-900 text-xs font-bold px-2.5 py-0.5 rounded-full">
        Amazon
      </span>
    );
  }
  return (
    <span className="inline-block bg-slate-200 text-slate-700 text-xs font-bold px-2.5 py-0.5 rounded-full">
      {source}
    </span>
  );
}
