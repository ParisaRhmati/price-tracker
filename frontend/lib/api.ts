/**
 * Tiny API client. Uses fetch + Next.js no-store cache so SSR pages always
 * see fresh data. All endpoints are typed.
 */

import {
  clearStoredPasscode,
  readStoredPasscode,
  writeStoredPasscode,
} from "./passcode";

// NEXT_PUBLIC_API_URL is "/api" — the browser uses that (it goes through the
// Next.js proxy/rewrite to the backend).
//
// But SERVER components (SSR, e.g. the product detail page) run inside Node in
// the frontend Docker container, where the browser proxy doesn't exist and
// "localhost" means the frontend container itself — NOT the backend. So for
// server-side fetches we must call the backend by its Docker service name,
// http://backend:8000. BACKEND_URL is set in the Dockerfile/compose to that.
const _rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

function resolveApiBase(): string {
  // Browser: use the relative/proxy URL as-is.
  if (typeof window !== "undefined") {
    return _rawApiUrl;
  }
  // Server-side: we need an absolute URL to the backend.
  // Prefer the explicit internal backend URL if provided.
  const internal =
    process.env.BACKEND_URL ||
    process.env.BACKEND_INTERNAL_URL ||
    "http://backend:8000";
  if (_rawApiUrl.startsWith("/")) {
    // e.g. "/api" -> "http://backend:8000/api"
    return `${internal.replace(/\/$/, "")}${_rawApiUrl}`;
  }
  // If NEXT_PUBLIC_API_URL was already absolute but points at localhost,
  // rewrite the host to the backend service so SSR can reach it in Docker.
  try {
    const u = new URL(_rawApiUrl);
    if (u.hostname === "localhost" || u.hostname === "127.0.0.1") {
      const b = new URL(internal);
      u.protocol = b.protocol;
      u.hostname = b.hostname;
      u.port = b.port;
      return u.toString().replace(/\/$/, "");
    }
  } catch {
    // fall through
  }
  return _rawApiUrl;
}

export const API_URL = resolveApiBase();

function buildHeaders(extra: HeadersInit = {}): Record<string, string> {
  const headers: Record<string, string> = {};
  Object.assign(headers, extra);
  const code = readStoredPasscode();
  if (code) {
    headers["X-App-Passcode"] = code;
  }
  return headers;
}

function onUnauthorized() {
  clearStoredPasscode();
  if (typeof window !== "undefined") {
    window.location.reload();
  }
}

// ---------- Types ----------
export type CrawlStatus = "pending" | "running" | "success" | "failed" | "blocked";
export type AvailabilityStatus = "unknown" | "in_stock" | "out_of_stock";

export interface SourceRef {
  website_name: string;
  price: number;
  url?: string;
}

export interface Brand {
  id: number;
  name: string;
  product_count: number;
}

export interface ProductListItem {
  id: number;
  model_name: string;
  display_name: string;
  brand: string | null;
  brand_id: number | null;
  updated_at: string;
  lowest_price: number | null;
  highest_price: number | null;
  price_spread: number | null;
  source_count: number;
  last_crawled_at: string | null;
  has_errors: boolean;
  cheapest_source: SourceRef | null;
  priciest_source: SourceRef | null;
  sources_ranked: SourceRef[];
  prices_by_website: Record<
    string,
    { price: number | null; url: string; availability: string }
  >;
}

export interface ProductSource {
  id: number;
  website_name: string;
  url: string;
  latest_price: number | null;
  currency: string;
  availability_status: AvailabilityStatus;
  last_crawled_at: string | null;
  crawl_status: CrawlStatus;
  error_message: string;
  consecutive_failures: number;
  is_lowest: boolean;
  is_highest: boolean;
  diff_vs_lowest: number | null;
}

export interface ProductDetail {
  id: number;
  model_name: string;
  display_name: string;
  brand: string | null;
  brand_id: number | null;
  created_at: string;
  updated_at: string;
  summary: {
    lowest_price: number | null;
    highest_price: number | null;
    price_spread: number | null;
    source_count: number;
  };
  sources: ProductSource[];
}

export interface DashboardData {
  total_products: number;
  total_sources: number;
  successful_crawls: number;
  failed_crawls: number;
  pending_crawls: number;
  cheapest_products: Array<{ id: number; model_name: string; lowest_price: number }>;
  recently_updated: Array<{ id: number; model_name: string; last_crawled_at: string }>;
  brands: Brand[];
  last_job: CrawlJob | null;
  generated_at: string;
}

export interface CrawlJob {
  id: number;
  started_at: string;
  finished_at: string | null;
  total: number;
  succeeded: number;
  failed: number;
  triggered_by: string;
  notes: string;
}

export interface PriceHistorySeries {
  product_id: number;
  series: Array<{
    source_id: number;
    website_name: string;
    url: string;
    points: Array<{ crawled_at: string; price: number; availability_status: string }>;
  }>;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ---------- Helpers ----------
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: buildHeaders({
      "Content-Type": "application/json",
      ...(init.headers || {}),
    }),
  });
  if (res.status === 401) {
    onUnauthorized();
    throw new Error("Passcode required");
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

// ---------- Endpoints ----------
export const api = {
  dashboard: () => request<DashboardData>("/dashboard/"),

  verifyPasscode: async (
    code: string
  ): Promise<{ ok: boolean; disabled?: boolean }> => {
    const res = await fetch(`${API_URL}/auth/check/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passcode: code }),
    });
    if (res.status === 401) {
      return { ok: false };
    }
    if (!res.ok) {
      throw new Error(`Passcode check failed: ${res.status}`);
    }
    return res.json();
  },

  listProducts: (params?: {
    search?: string;
    website?: string;
    brand?: string;
    ordering?: string;
    page?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.search) qs.set("search", params.search);
    if (params?.website) qs.set("website", params.website);
    if (params?.brand) qs.set("brand", params.brand);
    if (params?.ordering) qs.set("ordering", params.ordering);
    if (params?.page) qs.set("page", String(params.page));
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<Paginated<ProductListItem>>(`/products/${suffix}`);
  },

  product: (id: number | string) => request<ProductDetail>(`/products/${id}/`),

  productHistory: (id: number | string) =>
    request<PriceHistorySeries>(`/products/${id}/history/`),

  crawlProduct: (id: number | string) =>
    request<CrawlJob>(`/products/${id}/crawl/`, { method: "POST", body: "{}" }),

  triggerFullCrawl: (body: { website?: string; product_id?: number } = {}) =>
    request<CrawlJob>("/crawl/", { method: "POST", body: JSON.stringify(body) }),

  listJobs: () => request<Paginated<CrawlJob>>("/crawl-jobs/"),

  listFailedSources: () =>
    request<Paginated<ProductSource>>("/sources/?status=failed"),

  uploadExcel: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_URL}/import/`, {
      method: "POST",
      body: formData,
      headers: buildHeaders(),
    });
    if (res.status === 401) {
      onUnauthorized();
      throw new Error("Passcode required");
    }
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  downloadExcel: async (filters: { search?: string; website?: string } = {}) => {
    const qs = new URLSearchParams();
    if (filters.search) qs.set("search", filters.search);
    if (filters.website) qs.set("website", filters.website);
    const suffix = qs.toString() ? `?${qs}` : "";
    const res = await fetch(`${API_URL}/export/${suffix}`, {
      headers: buildHeaders(),
    });
    if (res.status === 401) {
      onUnauthorized();
      throw new Error("Passcode required");
    }
    if (!res.ok) {
      throw new Error(`Export failed: ${res.status} ${res.statusText}`);
    }
    const cd = res.headers.get("Content-Disposition") || "";
    const match = cd.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : "price-tracker-report.xlsx";
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};
