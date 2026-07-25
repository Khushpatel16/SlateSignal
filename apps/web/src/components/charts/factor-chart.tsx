"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatMoney } from "@/lib/format";
import type { ForecastResponse } from "@/types/domain";

export function FactorChart({
  factors,
}: {
  factors: ForecastResponse["factors"];
}) {
  const data = [...factors]
    .filter((factor) => factor.key !== "budget")
    .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact))
    .slice(0, 8)
    .reverse()
    .map((factor) => ({
      name: factor.label,
      impact: factor.impact / 1_000_000,
      rawImpact: factor.impact,
    }));

  return (
    <div className="h-[280px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 20, bottom: 4, left: 0 }}
        >
          <XAxis
            type="number"
            tickFormatter={(value) => `${value > 0 ? "+" : ""}$${value}M`}
            tick={{ fill: "#85837d", fontSize: 10 }}
            axisLine={{ stroke: "#303034" }}
            tickLine={false}
          />
          <YAxis
            dataKey="name"
            type="category"
            width={118}
            tick={{ fill: "#c9c6bd", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,0.03)" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const item = payload[0].payload as {
                name: string;
                rawImpact: number;
              };
              return (
                <div className="border border-[var(--line)] bg-[var(--surface-strong)] px-3 py-2 shadow-xl">
                  <p className="text-xs font-bold text-white">{item.name}</p>
                  <p
                    className={`tabular mt-1 text-xs ${
                      item.rawImpact >= 0
                        ? "text-[var(--positive)]"
                        : "text-[var(--negative)]"
                    }`}
                  >
                    {item.rawImpact >= 0 ? "+" : ""}
                    {formatMoney(item.rawImpact)}
                  </p>
                </div>
              );
            }}
          />
          <Bar dataKey="impact" radius={0}>
            {data.map((item) => (
              <Cell
                key={item.name}
                fill={item.impact >= 0 ? "#68c6a3" : "#ef746b"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
