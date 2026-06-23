"use client";

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import type { ScanStatusBreakdown } from "@/lib/types";

interface Props {
  data: ScanStatusBreakdown;
  title?: string;
}

const BARS = [
  { key: "completed", color: "#22c55e" },
  { key: "failed",    color: "#ef4444" },
  { key: "running",   color: "#3b82f6" },
  { key: "pending",   color: "#6b7280" },
] as const;

const TOOLTIP_STYLE = {
  contentStyle: { background: "#121821", border: "1px solid #22293580", borderRadius: 6 },
  labelStyle: { color: "#e5e7eb" },
  itemStyle: { color: "#9ca3af" },
};

export default function ScanStatusBar({ data, title = "Scans by status" }: Props) {
  // Single grouped bar — one entry with all statuses as separate bars.
  const chartData = [
    {
      name: "Scans",
      completed: data.completed,
      failed: data.failed,
      running: data.running,
      pending: data.pending,
    },
  ];

  const total = data.completed + data.failed + data.running + data.pending;

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <p className="mb-3 text-sm font-medium text-white">{title}</p>
      {total === 0 ? (
        <p className="py-8 text-center text-sm text-gray-500">No scans yet</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 11 }} />
            <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} allowDecimals={false} />
            <Tooltip {...TOOLTIP_STYLE} />
            <Legend
              iconType="square"
              iconSize={8}
              formatter={(v) => <span className="text-xs capitalize text-gray-400">{v}</span>}
            />
            {BARS.map((b) => (
              <Bar key={b.key} dataKey={b.key} fill={b.color} radius={[3, 3, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
