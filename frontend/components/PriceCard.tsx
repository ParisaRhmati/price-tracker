import { formatPrice } from "@/lib/format";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

interface PriceCardProps {
  label: string;
  price: number | null;
  variant?: "lowest" | "highest" | "spread";
  website?: string;
}

export default function PriceCard({ label, price, variant = "lowest", website }: PriceCardProps) {
  const variantStyles = {
    lowest: "border-good/40 bg-good-soft/30",
    highest: "border-ink-200 bg-ink-50",
    spread: "border-accent/40 bg-accent-soft/40",
  }[variant];

  const Icon = variant === "lowest" ? ArrowDownRight : variant === "highest" ? ArrowUpRight : null;

  return (
    <div className={`relative overflow-hidden rounded-2xl border p-6 ${variantStyles}`}>
      <div className="flex items-start justify-between">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-500">{label}</p>
        {Icon && <Icon className="h-4 w-4 text-ink-400" strokeWidth={1.5} />}
      </div>
      <p className="mt-4 font-display text-4xl font-semibold tracking-tight text-ink-900 price-num">
        {formatPrice(price)}
        <span className="ml-2 text-base font-normal text-ink-400">T</span>
      </p>
      {website && (
        <p className="mt-2 text-sm text-ink-500">
          at <span className="font-medium text-ink-700">{website}</span>
        </p>
      )}
    </div>
  );
}
