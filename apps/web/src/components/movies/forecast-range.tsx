import { formatMoney } from "@/lib/format";

export function ForecastRange({
  p10,
  p50,
  p90,
  compact = false,
}: {
  p10: number;
  p50: number;
  p90: number;
  compact?: boolean;
}) {
  const position = p90 > p10 ? ((p50 - p10) / (p90 - p10)) * 100 : 50;
  return (
    <div className="min-w-0">
      <div className="relative h-2 bg-[#2b2b2f]">
        <div className="absolute inset-0 bg-[var(--info)] opacity-45" />
        <span
          className="absolute top-1/2 h-4 w-0.5 -translate-y-1/2 bg-white"
          style={{ left: `${Math.min(98, Math.max(2, position))}%` }}
        />
      </div>
      <div
        className={`tabular mt-2 flex justify-between text-[10px] ${
          compact ? "text-[var(--muted)]" : "text-white/65"
        }`}
      >
        <span>P10 {formatMoney(p10, 0)}</span>
        <span className="font-extrabold text-white">
          P50 {formatMoney(p50, 0)}
        </span>
        <span>P90 {formatMoney(p90, 0)}</span>
      </div>
    </div>
  );
}
