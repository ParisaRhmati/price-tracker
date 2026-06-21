"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { RefreshCw } from "lucide-react";

export default function CrawlButton({ productId }: { productId: number }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const trigger = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const job = await api.crawlProduct(productId);
      setMessage(`Job #${job.id}: ${job.succeeded}/${job.total} ok`);
      router.refresh();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Crawl failed";
      setMessage(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col items-end gap-2">
      <button
        type="button"
        onClick={trigger}
        disabled={busy}
        className="inline-flex items-center gap-2 rounded-lg bg-ink-900 px-4 py-2 text-sm font-medium text-ink-50 transition hover:bg-ink-700 disabled:opacity-50"
      >
        <RefreshCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} />
        {busy ? "Crawling..." : "Crawl this product"}
      </button>
      {message && <p className="text-xs text-ink-500">{message}</p>}
    </div>
  );
}
