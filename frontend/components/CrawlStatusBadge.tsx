import type { CrawlStatus, AvailabilityStatus } from "@/lib/api";

const STATUS_STYLES: Record<CrawlStatus, string> = {
  pending: "bg-ink-100 text-ink-600 ring-ink-200",
  running: "bg-amber-50 text-amber-800 ring-amber-200",
  success: "bg-good-soft text-good ring-emerald-200",
  failed: "bg-bad-soft text-bad ring-red-200",
  blocked: "bg-bad-soft text-bad ring-red-300",
};

const STATUS_LABEL: Record<CrawlStatus, string> = {
  pending: "Pending",
  running: "Running",
  success: "Live",
  failed: "Failed",
  blocked: "Blocked",
};

export function CrawlStatusBadge({ status }: { status: CrawlStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${STATUS_STYLES[status]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {STATUS_LABEL[status]}
    </span>
  );
}

const AVAILABILITY_STYLES: Record<AvailabilityStatus, string> = {
  unknown: "bg-ink-100 text-ink-600 ring-ink-200",
  in_stock: "bg-good-soft text-good ring-emerald-200",
  out_of_stock: "bg-bad-soft text-bad ring-red-200",
};

const AVAILABILITY_LABEL: Record<AvailabilityStatus, string> = {
  unknown: "Unknown",
  in_stock: "In stock",
  out_of_stock: "Out of stock",
};

export function AvailabilityBadge({ status }: { status: AvailabilityStatus }) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${AVAILABILITY_STYLES[status]}`}
    >
      {AVAILABILITY_LABEL[status]}
    </span>
  );
}
