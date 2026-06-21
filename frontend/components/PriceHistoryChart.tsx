"use client";
import jalaali from "jalaali-js";
import type { PriceHistorySeries } from "@/lib/api";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import { formatPrice } from "@/lib/format";
import { useMemo } from "react";

// One distinct hue per source. Cycled when more sources than colors.
const SERIES_COLORS = ["#b45309", "#047857", "#1e40af", "#9d174d", "#4338ca", "#6b6759"];

interface ChartPoint {
  ts: number;
  label: string;
  [seriesKey: string]: number | string;
}

export default function PriceHistoryChart({ data }: { data: PriceHistorySeries }) {
  const { rows, websites } = useMemo(() => {
    // Build a unified set of timestamps across all sources, then fill values.
    const websiteSet = new Set<string>();
    const timestamps = new Set<string>();
    for (const series of data.series) {
      websiteSet.add(series.website_name);
      for (const point of series.points) timestamps.add(point.crawled_at);
    }
    const sortedTimestamps = [...timestamps].sort();
    const websites = [...websiteSet];

    // Last-known-value forward fill so a line doesn't break when a single
    // site fails to crawl at a particular timestamp.
    const lastSeen: Record<string, number | null> = {};
    for (const w of websites) lastSeen[w] = null;

    const jalaliMonths = [
      "Farv",
      "Ord",
      "Khor",
      "Tir",
      "Mor",
      "Shah",
      "Mehr",
      "Aban",
      "Azar",
      "Dey",
      "Bah",
      "Esf",
    ];

    const rows: ChartPoint[] = sortedTimestamps.map((ts) => {
      // Each source publishes 0 or 1 points at a given timestamp; build a lookup.
      for (const series of data.series) {
        const match = series.points.find((p) => p.crawled_at === ts);
        if (match) lastSeen[series.website_name] = Number(match.price);
      }
      const d = new Date(ts);
      const { jm, jd } = jalaali.toJalaali(d);
      const row: ChartPoint = {
        ts: d.getTime(),
        label: `${jd} ${jalaliMonths[jm - 1] ?? jm}`,
      };
      for (const w of websites) {
        if (lastSeen[w] !== null) row[w] = lastSeen[w] as number;
      }
      return row;
    });

    return { rows, websites };
  }, [data]);

  // Compute a tight Y-axis domain. Default Recharts behavior anchors the
  // axis at 0, which makes small price differences look like a flat line
  // when the prices themselves are in the tens of millions of toman. We
  // instead frame the chart around the actual price range with ~10% of
  // padding above and below so the lines breathe and movement is visible.
  const yDomain = useMemo<[number, number]>(() => {
    const values: number[] = [];
    for (const row of rows) {
      for (const w of websites) {
        const v = row[w];
        if (typeof v === "number" && Number.isFinite(v) && v > 0) {
          values.push(v);
        }
      }
    }
    if (values.length === 0) return [0, 0];
    const min = Math.min(...values);
    const max = Math.max(...values);
    if (min === max) {
      // Single flat price - give a small symmetric padding so the line
      // doesn't sit exactly on the axis edge.
      const pad = Math.max(min * 0.02, 1);
      return [min - pad, max + pad];
    }
    const padding = (max - min) * 0.2;
    return [Math.max(0, min - padding), max + padding];
  }, [rows, websites]);

  if (!rows.length) {
    return (
      <div className="rounded-xl border border-dashed border-ink-200 p-10 text-center text-sm text-ink-500">
        No price history yet. Trigger a crawl to start building one.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-ink-200 bg-white p-5">
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={rows} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
          <CartesianGrid stroke="#e6e3d8" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="label"
            stroke="#9a9485"
            fontSize={11}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="#9a9485"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => formatPrice(v)}
            width={70}
            domain={yDomain}
            allowDataOverflow={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#fafaf7",
              border: "1px solid #e6e3d8",
              borderRadius: "8px",
              fontSize: "12px",
            }}
            formatter={(value: number) => `${formatPrice(value)} T`}
          />
          <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
          {websites.map((website, idx) => (
            <Line
              key={website}
              type="monotone"
              dataKey={website}
              stroke={SERIES_COLORS[idx % SERIES_COLORS.length]}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
