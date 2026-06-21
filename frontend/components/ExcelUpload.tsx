"use client";
import { api } from "@/lib/api";
import { Upload, CheckCircle2, XCircle } from "lucide-react";
import { useRef, useState } from "react";

export default function ExcelUpload({ onImported }: { onImported?: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  const handleFile = async (file: File) => {
    setBusy(true);
    setResult(null);
    try {
      const report = await api.uploadExcel(file);
      const summary =
        `Imported ${report.products_created} new products and ${report.sources_created} sources` +
        ` across ${report.website_columns.length} sites.`;
      setResult({ ok: true, message: summary });
      onImported?.();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Upload failed";
      setResult({ ok: false, message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-2xl border border-ink-200 bg-white p-6">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h3 className="font-display text-xl font-semibold text-ink-900">Import Excel</h3>
          <p className="mt-1 text-sm text-ink-500">
            Upload <span className="font-mono text-xs">links.xlsx</span> to refresh product
            models and source URLs. The importer is idempotent.
          </p>
        </div>
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={busy}
          className="inline-flex items-center gap-2 rounded-lg bg-ink-900 px-4 py-2 text-sm font-medium text-ink-50 transition hover:bg-ink-700 disabled:opacity-50"
        >
          <Upload className="h-4 w-4" />
          {busy ? "Uploading..." : "Choose file"}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".xlsx,.xlsm"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
            e.target.value = "";
          }}
        />
      </div>
      {result && (
        <div
          className={`mt-5 flex items-start gap-2 rounded-lg border p-3 text-sm ${
            result.ok
              ? "border-good/30 bg-good-soft/40 text-good"
              : "border-bad/30 bg-bad-soft/40 text-bad"
          }`}
        >
          {result.ok ? (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          ) : (
            <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
          )}
          <span>{result.message}</span>
        </div>
      )}
    </div>
  );
}
