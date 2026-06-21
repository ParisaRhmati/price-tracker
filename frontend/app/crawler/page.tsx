"use client";
import { useEffect, useState } from "react";
import { api, type CrawlJob, type ProductSource } from "@/lib/api";
import { formatDateTime, formatRelativeTime } from "@/lib/format";
import ExcelUpload from "@/components/ExcelUpload";
import { CrawlStatusBadge } from "@/components/CrawlStatusBadge";
import { Play, RefreshCw, AlertTriangle, ExternalLink } from "lucide-react";

export default function CrawlerPage() {
  const [jobs, setJobs] = useState<CrawlJob[]>([]);
  const [failures, setFailures] = useState<ProductSource[]>([]);
  const [busy, setBusy] = useState(false);
  const [websiteFilter, setWebsiteFilter] = useState<string>("");
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    const [j, f] = await Promise.all([api.listJobs(), api.listFailedSources()]);
    setJobs(j.results);
    setFailures(f.results);
  };

  useEffect(() => {
    load().catch(() => undefined);
    const interval = setInterval(() => load().catch(() => undefined), 8000);
    return () => clearInterval(interval);
  }, []);

  const trigger = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const job = await api.triggerFullCrawl({
        website: websiteFilter || undefined,
      });
      setMessage(`Job #${job.id}: ${job.succeeded}/${job.total} ok · ${job.failed} failed`);
      await load();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Crawl failed";
      setMessage(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-10">
      <header className="border-b border-ink-200 pb-8">
        <p className="text-xs uppercase tracking-[0.2em] text-ink-500">Operations</p>
        <h1 className="mt-2 font-display text-5xl font-semibold tracking-tight text-ink-900">
          Crawler
        </h1>
        <p className="mt-3 max-w-xl text-ink-500">
          Import data, trigger crawls, and inspect failures. The list refreshes every 8s.
        </p>
      </header>

      <ExcelUpload onImported={load} />

      <section className="rounded-2xl border border-ink-200 bg-white p-6">
        <h2 className="font-display text-xl font-semibold text-ink-900">Trigger a crawl</h2>
        <p className="mt-1 text-sm text-ink-500">
          Run all sources or filter to one website. For very large batches, prefer the
          management command.
        </p>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <select
            value={websiteFilter}
            onChange={(e) => setWebsiteFilter(e.target.value)}
            className="rounded-lg border border-ink-200 bg-white px-3 py-2.5 text-sm"
          >
            <option value="">All sources</option>
            <option value="digikala.com">digikala.com</option>
            <option value="techno life">techno life</option>
            <option value="mobile 140">mobile 140</option>
          </select>
          <button
            type="button"
            onClick={trigger}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-accent/90 disabled:opacity-50"
          >
            {busy ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {busy ? "Crawling..." : "Crawl now"}
          </button>
          {message && <span className="text-sm text-ink-500">{message}</span>}
        </div>
      </section>

      <section>
        <h2 className="mb-4 font-display text-2xl font-semibold text-ink-900">
          Recent jobs
        </h2>
        {jobs.length === 0 ? (
          <div className="rounded-xl border border-dashed border-ink-200 p-10 text-center text-ink-500">
            No crawl jobs yet.
          </div>
        ) : (
          <div className="overflow-hidden rounded-2xl border border-ink-200 bg-white">
            <table className="min-w-full divide-y divide-ink-200 text-sm">
              <thead className="bg-ink-50/60 text-left text-xs uppercase tracking-[0.14em] text-ink-500">
                <tr>
                  <th className="px-5 py-3.5 font-medium">Job</th>
                  <th className="px-5 py-3.5 font-medium">Started</th>
                  <th className="px-5 py-3.5 font-medium">Finished</th>
                  <th className="px-5 py-3.5 font-medium">Total</th>
                  <th className="px-5 py-3.5 font-medium">Success</th>
                  <th className="px-5 py-3.5 font-medium">Failed</th>
                  <th className="px-5 py-3.5 font-medium">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-100">
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td className="px-5 py-3 font-medium text-ink-800">#{job.id}</td>
                    <td className="px-5 py-3 text-ink-600">{formatDateTime(job.started_at)}</td>
                    <td className="px-5 py-3 text-ink-600">
                      {job.finished_at ? formatRelativeTime(job.finished_at) : "—"}
                    </td>
                    <td className="px-5 py-3 text-ink-700">{job.total}</td>
                    <td className="px-5 py-3 text-good">{job.succeeded}</td>
                    <td className="px-5 py-3 text-bad">{job.failed}</td>
                    <td className="px-5 py-3">
                      <span className="rounded-full bg-ink-100 px-2 py-0.5 text-xs uppercase tracking-wider text-ink-600">
                        {job.triggered_by}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-4 flex items-center gap-2 font-display text-2xl font-semibold text-ink-900">
          <AlertTriangle className="h-5 w-5 text-bad" />
          Failed URLs
          <span className="ml-2 rounded-full bg-bad-soft px-2 py-0.5 text-xs font-medium text-bad">
            {failures.length}
          </span>
        </h2>
        {failures.length === 0 ? (
          <div className="rounded-xl border border-dashed border-ink-200 p-10 text-center text-ink-500">
            No failures. Nice.
          </div>
        ) : (
          <ul className="space-y-2">
            {failures.map((source) => (
              <li
                key={source.id}
                className="rounded-xl border border-bad/20 bg-bad-soft/30 p-4"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="font-display text-lg text-ink-900">
                    {source.website_name}
                  </span>
                  <CrawlStatusBadge status={source.crawl_status} />
                </div>
                <p className="mt-1 text-xs text-bad">{source.error_message}</p>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-flex items-center gap-1 text-xs text-ink-600 hover:text-ink-900"
                >
                  {source.url.slice(0, 80)}... <ExternalLink className="h-3 w-3" />
                </a>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
