"use client";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, type ProductListItem } from "@/lib/api";
import ProductTable from "@/components/ProductTable";
import { Search, ArrowUpDown, Download } from "lucide-react";

type SortKey = "model_name" | "low_asc" | "low_desc" | "updated";

interface Brand {
  id: number;
  name: string;
  product_count: number;
}

// Inner component that uses useSearchParams — must be inside <Suspense>
function ProductsPageInner() {
  const searchParams = useSearchParams();
  const [products, setProducts] = useState<ProductListItem[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [website, setWebsite] = useState<string>("");
  const [brand, setBrand] = useState<string>(searchParams?.get("brand") ?? "");
  const [sort, setSort] = useState<SortKey>("model_name");
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    api.dashboard().then((data: any) => {
      if (data?.brands) setBrands(data.brands);
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api
      .listProducts({
        search: search || undefined,
        website: website || undefined,
        brand: brand || undefined,
      })
      .then((page) => { if (alive) setProducts(page.results); })
      .catch((err: Error) => alive && setError(err.message))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [search, website, brand]);

  const websites = ["digikala.com", "techno life", "mobile 140"];

  const sorted = useMemo(() => {
    const copy = [...products];
    switch (sort) {
      case "low_asc":
        return copy.sort((a, b) => (a.lowest_price ?? Infinity) - (b.lowest_price ?? Infinity));
      case "low_desc":
        return copy.sort((a, b) => (b.lowest_price ?? -Infinity) - (a.lowest_price ?? -Infinity));
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
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-ink-200 pb-8">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-ink-500">Catalogue</p>
          <h1 className="mt-2 font-display text-5xl font-semibold tracking-tight text-ink-900">
            Products
          </h1>
          <p className="mt-3 max-w-xl text-ink-500">
            Browse every tracked product model and compare prices across sources.
          </p>
        </div>
        <button
          type="button"
          onClick={async () => {
            setExporting(true);
            setError(null);
            try {
              await api.downloadExcel({ search: search || undefined, website: website || undefined });
            } catch (err) {
              setError(err instanceof Error ? err.message : "Export failed");
            } finally {
              setExporting(false);
            }
          }}
          disabled={exporting}
          className="inline-flex items-center gap-2 rounded-lg bg-ink-900 px-4 py-2.5 text-sm font-medium text-ink-50 transition hover:bg-ink-700 disabled:opacity-50"
        >
          <Download className={`h-4 w-4 ${exporting ? "animate-pulse" : ""}`} />
          {exporting ? "Building report..." : "Download Excel"}
        </button>
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

        {brands.length > 0 && (
          <select
            value={brand}
            onChange={(e) => setBrand(e.target.value)}
            className="rounded-lg border border-ink-200 bg-white px-3 py-2.5 text-sm focus:border-ink-700 focus:outline-none"
          >
            <option value="">All brands</option>
            {brands.map((b) => (
              <option key={b.id} value={String(b.id)}>
                {b.name} ({b.product_count})
              </option>
            ))}
          </select>
        )}

        <select
          value={website}
          onChange={(e) => setWebsite(e.target.value)}
          className="rounded-lg border border-ink-200 bg-white px-3 py-2.5 text-sm focus:border-ink-700 focus:outline-none"
        >
          <option value="">All sources</option>
          {websites.map((w) => (
            <option key={w} value={w}>{w}</option>
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

// Outer component wraps inner in Suspense (required for useSearchParams in Next.js production)
export default function ProductsPage() {
  return (
    <Suspense fallback={
      <div className="p-12 text-center text-ink-400">Loading...</div>
    }>
      <ProductsPageInner />
    </Suspense>
  );
}
