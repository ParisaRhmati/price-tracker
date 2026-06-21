import Link from "next/link";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import PriceCard from "@/components/PriceCard";
import PriceComparisonTable from "@/components/PriceComparisonTable";
import PriceHistoryChart from "@/components/PriceHistoryChart";
import CrawlButton from "./CrawlButton";
import { ChevronLeft } from "lucide-react";

export const dynamic = "force-dynamic";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function ProductDetailPage({ params }: PageProps) {
  const { id } = await params;
  const [product, history] = await Promise.all([
    api.product(id),
    api.productHistory(id),
  ]);

  const lowestSource = product.sources.find((s) => s.is_lowest);
  const highestSource = product.sources.find((s) => s.is_highest);

  return (
    <div className="space-y-10">
      <div>
        <Link
          href="/products"
          className="inline-flex items-center gap-1 text-sm text-ink-500 transition hover:text-ink-900"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to products
        </Link>
      </div>

      <header className="border-b border-ink-200 pb-8">
        <p className="text-xs uppercase tracking-[0.2em] text-ink-500">Product model</p>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
          <h1 className="font-display text-5xl font-semibold tracking-tight text-ink-900">
            {product.model_name}
          </h1>
          <CrawlButton productId={product.id} />
        </div>
        <p className="mt-3 text-sm text-ink-500">
          Tracking <span className="font-medium text-ink-700">{product.summary.source_count}</span>{" "}
          sources · added {formatDateTime(product.created_at)}
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <PriceCard
          label="Lowest price"
          price={product.summary.lowest_price}
          variant="lowest"
          website={lowestSource?.website_name}
        />
        <PriceCard
          label="Highest price"
          price={product.summary.highest_price}
          variant="highest"
          website={highestSource?.website_name}
        />
        <PriceCard
          label="Spread"
          price={product.summary.price_spread}
          variant="spread"
        />
      </section>

      <section>
        <h2 className="mb-4 font-display text-2xl font-semibold text-ink-900">
          Source comparison
        </h2>
        <PriceComparisonTable sources={product.sources} />
      </section>

      <section>
        <h2 className="mb-4 font-display text-2xl font-semibold text-ink-900">
          Price history
        </h2>
        <PriceHistoryChart data={history} />
      </section>
    </div>
  );
}
