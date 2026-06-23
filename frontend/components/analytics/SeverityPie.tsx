"use client";

import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import type { SeverityBreakdown } from "@/lib/types";

const SLICES = [
  { key: "critical", label: "Critical", color: "#ef4444" },
  { key: "high",     label: "High",     color: "#f97316" },
  { key: "medium",   label: "Medium",   color: "#eab308" },
  { key: "low",      label: "Low",      color: "#22c55e" },
] as const;

interface Props {
  data: SeverityBreakdown;
  title?: string;
}

export default function SeverityPie({ data, title = "Alerts by severity" }: Props) {
  const slices = SLICES.map((s) => ({ name: s.label, value: data[s.key], color: s.color }))
    .filter((s) => s.value > 0);

  const empty = slices.length === 0;

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <p className="mb-3 text-sm font-medium text-white">{title}</p>
      {empty ? (
        <p className="py-8 text-center text-sm text-gray-500">No alerts yet</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={slices}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={80}
              strokeWidth={0}
            >
              {slices.map((s) => (
                <Cell key={s.name} fill={s.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ background: "#121821", border: "1px solid #22293580", borderRadius: 6 }}
              labelStyle={{ color: "#e5e7eb" }}
              itemStyle={{ color: "#9ca3af" }}
            />
            <Legend
              iconType="circle"
              iconSize={8}
              formatter={(v) => <span className="text-xs text-gray-400">{v}</span>}
            />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}