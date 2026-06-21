import type { ProductSource } from "@/lib/api";
import { formatPrice, formatDiff, formatRelativeTime } from "@/lib/format";
import { CrawlStatusBadge, AvailabilityBadge } from "./CrawlStatusBadge";
import { ExternalLink, AlertTriangle } from "lucide-react";

export default function PriceComparisonTable({ sources }: { sources: ProductSource[] }) {
  if (!sources.length) {
    return (
      <div className="rounded-xl border border-dashed border-ink-200 p-10 text-center text-ink-500">
        No sources for this product yet.
      </div>
    );
  }

  // Sort so the lowest price appears first; nulls drift to the bottom.
  const ordered = [...sources].sort((a, b) => {
    if (a.latest_price === null) return 1;
    if (b.latest_price === null) return -1;
    return Number(a.latest_price) - Number(b.latest_price);
  });

  return (
    <div className="rounded-xl border border-ink-200 bg-white">
      <table className="min-w-full divide-y divide-ink-200 text-sm">
        <thead className="sticky top-0 z-10 bg-ink-50 shadow-[0_1px_0_0_rgba(0,0,0,0.06)]">
          <tr className="text-left text-xs uppercase tracking-[0.14em] text-ink-500">
            <th className="px-5 py-3.5 font-medium">Website</th>
            <th className="px-5 py-3.5 font-medium">Price</th>
            <th className="px-5 py-3.5 font-medium">vs lowest</th>
            <th className="px-5 py-3.5 font-medium">Availability</th>
            <th className="px-5 py-3.5 font-medium">Status</th>
            <th className="px-5 py-3.5 font-medium">Last update</th>
            <th className="px-5 py-3.5 font-medium" />
          </tr>
        </thead>
        <tbody className="divide-y divide-ink-100">
          {ordered.map((source) => {
            const isLowest = source.is_lowest && source.latest_price !== null;
            return (
              <tr
                key={source.id}
                className={`transition-colors ${
                  isLowest ? "bg-good-soft/30" : "hover:bg-ink-50/50"
                }`}
              >
                <td className="px-5 py-4">
                  <div className="flex items-center gap-2">
                    {isLowest && (
                      <span className="rounded-sm bg-good px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white">
                        Best
                      </span>
                    )}
                    <span className="font-medium text-ink-800">{source.website_name}</span>
                  </div>
                </td>
                <td className="px-5 py-4">
                  {source.latest_price === null ? (
                    // No price: render the soft-red "Out of stock" badge that
                    // also links to the website's product page.
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noreferrer"
                      title="Out of stock — click to open the product page"
                      className="inline-flex items-center gap-1.5 rounded-full bg-bad-soft px-3 py-1 text-xs font-medium text-bad ring-1 ring-inset ring-red-200 transition hover:bg-red-100 hover:ring-red-300"
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-bad opacity-80" />
                      Out of stock
                      <ExternalLink className="h-3 w-3 opacity-60" />
                    </a>
                  ) : (
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noreferrer"
                      title={`Open ${source.website_name} product page`}
                      className={`price-num group inline-flex items-baseline gap-1.5 rounded-md px-1.5 py-0.5 font-display text-lg transition hover:bg-ink-50 ${
                        isLowest ? "font-semibold text-good hover:bg-emerald-50" : "text-ink-900"
                      }`}
                    >
                      {formatPrice(source.latest_price)}
                      <span className="text-xs text-ink-400">T</span>
                    </a>
                  )}
                </td>
                <td className="px-5 py-4">
                  {source.diff_vs_lowest === null ? (
                    <span className="text-ink-400">—</span>
                  ) : source.diff_vs_lowest === 0 || isLowest ? (
                    <span className="text-good">—</span>
                  ) : (
                    <span className="price-num text-ink-600">
                      +{formatDiff(source.diff_vs_lowest)}
                    </span>
                  )}
                </td>
                <td className="px-5 py-4">
                  <AvailabilityBadge status={source.availability_status} />
                </td>
                <td className="px-5 py-4">
                  <CrawlStatusBadge status={source.crawl_status} />
                  {source.error_message && (
                    <div className="mt-1.5 flex items-start gap-1 text-xs text-bad">
                      <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                      <span className="line-clamp-2">{source.error_message}</span>
                    </div>
                  )}
                </td>
                <td className="px-5 py-4 text-ink-500">
                  {formatRelativeTime(source.last_crawled_at)}
                </td>
                <td className="px-5 py-4 text-right">
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs font-medium text-ink-600 hover:text-ink-900"
                  >
                    Open <ExternalLink className="h-3 w-3" />
                  </a>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
