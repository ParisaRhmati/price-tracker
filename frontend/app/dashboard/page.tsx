import Link from "next/link";
import { api } from "@/lib/api";
import { formatPrice, formatRelativeTime, formatDateTime } from "@/lib/format";
import { ArrowDownRight, Clock, Database, CircleAlert, CircleCheck, Tag } from "lucide-react";

export const dynamic = "force-dynamic";

function StatCard({
  label,
  value,
  hint,
  Icon,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  hint?: string;
  Icon: typeof Database;
  tone?: "neutral" | "good" | "bad";
}) {
  const toneStyles =
    tone === "good"
      ? "text-good"
      : tone === "bad"
        ? "text-bad"
        : "text-ink-900";
  return (
    <div className="rounded-2xl border border-ink-200 bg-white p-6">
      <div className="flex items-start justify-between">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-500">{label}</p>
        <Icon className="h-4 w-4 text-ink-400" strokeWidth={1.5} />
      </div>
      <p className={`mt-3 font-display text-4xl font-semibold tracking-tight price-num ${toneStyles}`}>
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-ink-400">{hint}</p>}
    </div>
  );
}

export default async function DashboardPage() {
  const data = await api.dashboard();

  return (
    <div className="space-y-10">
      <header className="flex items-end justify-between border-b border-ink-200 pb-8">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-ink-500">Overview</p>
          <h1 className="mt-2 font-display text-5xl font-semibold tracking-tight text-ink-900">
            Dashboard
          </h1>
          <p className="mt-3 max-w-xl text-ink-500">
            A snapshot of every product, every source, and every price the crawler has
            collected.
          </p>
        </div>
        <p className="text-xs text-ink-400">
          Generated {formatRelativeTime(data.generated_at)}
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Products" value={data.total_products} Icon={Database} />
        <StatCard
          label="Tracked URLs"
          value={data.total_sources}
          hint={`${data.pending_crawls} pending`}
          Icon={Database}
        />
        <StatCard
          label="Successful crawls"
          value={data.successful_crawls}
          Icon={CircleCheck}
          tone="good"
        />
        <StatCard
          label="Failures"
          value={data.failed_crawls}
          Icon={CircleAlert}
          tone={data.failed_crawls > 0 ? "bad" : "neutral"}
        />
      </section>

      {/* Brand filter — only shown once brands are in the API response */}
      {data.brands && data.brands.length > 0 && (
        <section>
          <h2 className="flex items-center gap-2 font-display text-xl font-semibold text-ink-900 mb-4">
            <Tag className="h-5 w-5 text-ink-400" strokeWidth={1.5} />
            Filter by brand
          </h2>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/products"
              className="inline-flex items-center gap-2 rounded-xl border border-ink-200 bg-white px-5 py-3 text-sm font-medium text-ink-700 transition hover:border-ink-400 hover:bg-ink-50"
            >
              All brands
              <span className="rounded-full bg-ink-100 px-2 py-0.5 text-xs text-ink-500">
                {data.total_products}
              </span>
            </Link>
            {data.brands.map((brand) => (
              <Link
                key={brand.id}
                href={`/products?brand=${brand.id}`}
                className="inline-flex items-center gap-2 rounded-xl border border-ink-200 bg-white px-5 py-3 text-sm font-medium text-ink-700 transition hover:border-ink-400 hover:bg-ink-50"
              >
                {brand.name}
                <span className="rounded-full bg-ink-100 px-2 py-0.5 text-xs text-ink-500">
                  {brand.product_count}
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-ink-200 bg-white p-6">
          <h2 className="flex items-center gap-2 font-display text-xl font-semibold text-ink-900">
            <ArrowDownRight className="h-5 w-5 text-good" />
            Cheapest right now
          </h2>
          {data.cheapest_products.length === 0 ? (
            <p className="mt-4 text-sm text-ink-500">
              No prices collected yet. Trigger a crawl from the Crawler page.
            </p>
          ) : (
            <ul className="mt-4 divide-y divide-ink-100">
              {data.cheapest_products.map((p) => (
                <li key={p.id} className="flex items-center justify-between py-3">
                  <Link
                    href={`/products/${p.id}`}
                    className="font-display text-lg text-ink-800 hover:text-accent"
                  >
                    {p.model_name}
                  </Link>
                  <span className="price-num font-medium text-good">
                    {formatPrice(p.lowest_price)}{" "}
                    <span className="text-xs text-ink-400">T</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-2xl border border-ink-200 bg-white p-6">
          <h2 className="flex items-center gap-2 font-display text-xl font-semibold text-ink-900">
            <Clock className="h-5 w-5 text-ink-500" />
            Recently updated
          </h2>
          {data.recently_updated.length === 0 ? (
            <p className="mt-4 text-sm text-ink-500">No crawls yet.</p>
          ) : (
            <ul className="mt-4 divide-y divide-ink-100">
              {data.recently_updated.map((p) => (
                <li key={p.id} className="flex items-center justify-between py-3">
                  <Link
                    href={`/products/${p.id}`}
                    className="font-display text-lg text-ink-800 hover:text-accent"
                  >
                    {p.model_name}
                  </Link>
                  <span className="text-xs text-ink-500">
                    {formatRelativeTime(p.last_crawled_at)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {data.last_job && (
        <section className="rounded-2xl border border-ink-200 bg-ink-50/60 p-6">
          <p className="text-xs uppercase tracking-[0.18em] text-ink-500">Latest crawl run</p>
          <div className="mt-3 flex flex-wrap items-baseline gap-x-6 gap-y-2">
            <span className="font-display text-2xl text-ink-900">Job #{data.last_job.id}</span>
            <span className="text-sm text-ink-600">
              {data.last_job.succeeded} succeeded · {data.last_job.failed} failed of{" "}
              {data.last_job.total}
            </span>
            <span className="text-sm text-ink-500">
              started {formatDateTime(data.last_job.started_at)}
            </span>
            <span className="rounded-full bg-ink-200 px-2 py-0.5 text-xs uppercase tracking-wider text-ink-600">
              {data.last_job.triggered_by}
            </span>
          </div>
        </section>
      )}
    </div>
  );
}
