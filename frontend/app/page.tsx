"use client";
import { useEffect, useMemo, useState } from "react";
import { api, type ProductListItem } from "@/lib/api";
import ProductTable from "@/components/ProductTable";
import { Search, ArrowUpDown } from "lucide-react";

type SortKey = "model_name" | "low_asc" | "low_desc" | "updated";

export default function ProductsPage() {
  const [products, setProducts] = useState<ProductListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [website, setWebsite] = useState<string>("");
  const [sort, setSort] = useState<SortKey>("model_name");

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api
      .listProducts({ search: search || undefined, website: website || undefined })
      .then((page) => {
        if (alive) setProducts(page.results);
      })
      .catch((err: Error) => alive && setError(err.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [search, website]);

  // Build the website filter list from whatever products are loaded.
  // For a cleaner UX we hard-code the two known sources from the spreadsheet.
  const websites = ["digikala.com", "techno life"];

  const sorted = useMemo(() => {
    const copy = [...products];
    switch (sort) {
      case "low_asc":
        return copy.sort(
          (a, b) => (a.lowest_price ?? Infinity) - (b.lowest_price ?? Infinity)
        );
      case "low_desc":
        return copy.sort(
          (a, b) => (b.lowest_price ?? -Infinity) - (a.lowest_price ?? -Infinity)
        );
      case "updated":
        return copy.sort((a, b) => {
          const aT = a.last_crawled_at ? new Date(a.last_crawled_at).getTime() : 0;
          const bT = b.last_crawled_at ? new Date(b.last_crawled_at).getTime() : 0;
          return bT - aT;
        });
      default:
        return copy.sort((a, b) => a.model_name.localeCompare(b.model_name));
    }
  }, [products, sort]);

  return (
    <div className="space-y-8">
      <header className="border-b border-ink-200 pb-8">
        <p className="text-xs uppercase tracking-[0.2em] text-ink-500">Catalogue</p>
        <h1 className="mt-2 font-display text-5xl font-semibold tracking-tight text-ink-900">
          Products
        </h1>
        <p className="mt-3 max-w-xl text-ink-500">
          Browse every tracked product model and compare prices across sources.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
          <input
            type="text"
            placeholder="Search by model name (e.g. a07)"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-ink-200 bg-white py-2.5 pl-10 pr-3 text-sm focus:border-ink-700 focus:outline-none focus:ring-1 focus:ring-ink-700"
          />
        </div>
        <select
          value={website}
          onChange={(e) => setWebsite(e.target.value)}
          className="rounded-lg border border-ink-200 bg-white px-3 py-2.5 text-sm focus:border-ink-700 focus:outline-none"
        >
          <option value="">All sources</option>
          {websites.map((w) => (
            <option key={w} value={w}>
              {w}
            </option>
          ))}
        </select>
        <div className="relative">
          <ArrowUpDown className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            className="rounded-lg border border-ink-200 bg-white py-2.5 pl-10 pr-3 text-sm focus:border-ink-700 focus:outline-none"
          >
            <option value="model_name">Sort: Model</option>
            <option value="low_asc">Sort: Lowest price ↑</option>
            <option value="low_desc">Sort: Lowest price ↓</option>
            <option value="updated">Sort: Recently updated</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-bad/30 bg-bad-soft/40 p-4 text-sm text-bad">
          {error}
        </div>
      )}

      {loading ? (
        <div className="rounded-2xl border border-ink-200 bg-white p-12 text-center text-ink-400">
          Loading...
        </div>
      ) : (
        <ProductTable products={sorted} />
      )}
    </div>
  );
}
