"use client";
import Link from "next/link";
import type { ProductListItem } from "@/lib/api";
import { formatPrice, formatRelativeTime } from "@/lib/format";
import { AlertTriangle, ArrowRight, ExternalLink } from "lucide-react";

const COLUMN_LABELS: Record<string, string> = {
  digikala: "digikala",
  technolife: "techno life",
  mobile140: "mobile 140",
  hamrahtel: "hamrahtel",
  kasrapars: "kasrapars",
};

// Fixed left-to-right column order. Any website not listed here is appended
// afterwards in the order it's first seen.
const PREFERRED_ORDER = ["digikala", "technolife", "mobile140", "hamrahtel", "kasrapars"];

function columnKey(name: string): string {
  const lower = name.toLowerCase();
  if (lower.includes("digikala")) return "digikala";
  if (lower.includes("technolife") || lower === "techno life") return "technolife";
  if (lower.includes("mobile140") || lower === "mobile 140") return "mobile140";
  if (lower.includes("hamrahtel") || lower === "hamrah tel") return "hamrahtel";
  if (lower.includes("kasrapars") || lower === "kasra pars" || lower.includes("کسری")) return "kasrapars";
  return lower;
}

function friendlyLabel(name: string): string {
  return COLUMN_LABELS[columnKey(name)] ?? name;
}

// Website names to skip — these are metadata fields, not price sources.
const SKIP_KEYS = new Set(["brand", "brand_id"]);

type Cell = {
  price: number | null;
  url: string;
  availability: string;
} | null;

export default function ProductTable({ products }: { products: ProductListItem[] }) {
  if (!products.length) {
    return (
      <div className="rounded-xl border border-dashed border-ink-200 p-12 text-center">
        <p className="text-ink-500">No products match the filters.</p>
      </div>
    );
  }

  // Collect every website key present in the data.
  const seen: Record<string, string> = {};
  for (const product of products) {
    for (const websiteName of Object.keys(product.prices_by_website ?? {})) {
      if (SKIP_KEYS.has(websiteName.toLowerCase())) continue;
      const key = columnKey(websiteName);
      if (!(key in seen)) {
        seen[key] = friendlyLabel(websiteName);
      }
    }
  }

  // Build the column order: preferred sources first (in our fixed order),
  // then any others that happen to exist, in discovery order.
  const columnOrder: string[] = [];
  const columnDisplay: Record<string, string> = {};
  for (const key of PREFERRED_ORDER) {
    if (key in seen) {
      columnOrder.push(key);
      columnDisplay[key] = seen[key];
    }
  }
  for (const key of Object.keys(seen)) {
    if (!columnOrder.includes(key)) {
      columnOrder.push(key);
      columnDisplay[key] = seen[key];
    }
  }

  function cellFor(product: ProductListItem, key: string): Cell {
    for (const [name, payload] of Object.entries(product.prices_by_website ?? {})) {
      if (SKIP_KEYS.has(name.toLowerCase())) continue;
      if (columnKey(name) === key) return payload as Cell;
    }
    return null;
  }

  return (
    <div className="rounded-2xl border border-ink-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-ink-200 text-sm">
        <thead className="sticky top-0 z-10 bg-ink-50 shadow-[0_1px_0_0_rgba(0,0,0,0.06)]">
          <tr className="text-left text-xs uppercase tracking-[0.14em] text-ink-500">
            <th className="px-6 py-4 font-medium">Model</th>
            {columnOrder.map((key) => (
              <th key={key} className="px-6 py-4 font-medium">
                {columnDisplay[key]}
              </th>
            ))}
            <th className="px-6 py-4 font-medium">Updated</th>
            <th className="px-6 py-4 font-medium" />
          </tr>
        </thead>
        <tbody className="divide-y divide-ink-100">
          {products.map((product) => {
            const cells = columnOrder.map((key) => ({
              key,
              data: cellFor(product, key),
            }));
            const inStockPrices = cells
              .map((c) =>
                c.data &&
                c.data.price != null &&
                c.data.availability !== "out_of_stock"
                  ? c.data.price
                  : null
              )
              .filter((p): p is number => p != null);
            const minPrice = inStockPrices.length
              ? Math.min(...inStockPrices)
              : null;
            const hasMultipleInStock = inStockPrices.length > 1;

            return (
              <tr
                key={product.id}
                className="transition-colors hover:bg-ink-50/40"
              >
                <td className="px-6 py-4">
                  <Link
                    href={`/products/${product.id}`}
                    className="group inline-flex items-center gap-2"
                  >
                    <span className="font-display text-lg text-ink-900 group-hover:text-accent">
                      {product.model_name}
                    </span>
                    {product.has_errors && (
                      <AlertTriangle
                        className="h-4 w-4 text-bad"
                        strokeWidth={1.8}
                      />
                    )}
                  </Link>
                </td>

                {cells.map(({ key, data }) => {
                  if (!data) {
                    return (
                      <td key={key} className="px-6 py-4 text-ink-400">
                        —
                      </td>
                    );
                  }

                  const isOutOfStock = data.availability === "out_of_stock";
                  const isWinner =
                    !isOutOfStock &&
                    data.price === minPrice &&
                    hasMultipleInStock;

                  if (isOutOfStock || data.price == null) {
                    return (
                      <td key={key} className="px-6 py-4">
                        <a
                          href={data.url}
                          target="_blank"
                          rel="noreferrer"
                          title="Out of stock — click to open the product page"
                          className="inline-flex items-center gap-1.5 rounded-full bg-bad-soft px-3 py-1 text-xs font-medium text-bad ring-1 ring-inset ring-red-200 transition hover:bg-red-100 hover:ring-red-300"
                        >
                          <span className="h-1.5 w-1.5 rounded-full bg-bad opacity-80" />
                          Out of stock
                          <ExternalLink className="h-3 w-3 opacity-60" />
                        </a>
                      </td>
                    );
                  }

                  return (
                    <td key={key} className="px-6 py-4">
                      <a
                        href={data.url}
                        target="_blank"
                        rel="noreferrer"
                        title={`Open on ${columnDisplay[key]}`}
                        className={`price-num group inline-flex items-center gap-1 rounded-md px-2 py-1 font-semibold transition ${
                          isWinner
                            ? "bg-good-soft text-good ring-1 ring-inset ring-emerald-200 hover:bg-emerald-100"
                            : "text-ink-800 hover:bg-ink-50 hover:text-accent"
                        }`}
                      >
                        {formatPrice(data.price)}
                        <ExternalLink className="h-3 w-3 opacity-0 transition group-hover:opacity-70" />
                      </a>
                    </td>
                  );
                })}

                <td className="px-6 py-4 text-ink-500">
                  {formatRelativeTime(product.last_crawled_at)}
                </td>

                <td className="px-6 py-4 text-right">
                  <Link
                    href={`/products/${product.id}`}
                    className="inline-flex items-center gap-1 text-xs font-medium text-ink-500 hover:text-ink-900"
                  >
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
