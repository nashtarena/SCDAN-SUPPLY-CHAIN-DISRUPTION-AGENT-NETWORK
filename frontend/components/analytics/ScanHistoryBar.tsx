"use client";

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import type { ScanHistoryEntry } from "@/lib/types";

interface Props {
  data: ScanHistoryEntry[];
  title?: string;
}

function shortId(id: string) {
  return id.slice(0, 6) + "…";
}

function statusColor(status: string) {
  return status === "completed" ? "#22c55e" : "#ef4444";
}

export default function ScanHistoryBar({ data, title = "Recent scans" }: Props) {
  if (data.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="mb-3 text-sm font-medium text-white">{title}</p>
        <p className="py-8 text-center text-sm text-gray-500">No scans yet</p>
      </div>
    );
  }

  // Show newest-first, cap at 10 for readability.
  const chartData = [...data].slice(0, 10).reverse().map((s) => ({
    name: shortId(s.scan_id),
    alerts: s.alert_count,
    status: s.status,
    date: s.completed_at ? new Date(s.completed_at).toLocaleDateString() : "—",
  }));

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <p className="mb-3 text-sm font-medium text-white">{title}</p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 10 }} />
          <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} allowDecimals={false} />
          <Tooltip
            contentStyle={{ background: "#121821", border: "1px solid #22293580", borderRadius: 6 }}
            labelStyle={{ color: "#e5e7eb" }}
            itemStyle={{ color: "#9ca3af" }}
            formatter={(value, _name, props) => [
              `${value} alerts (${props.payload.status})`,
              "Scan",
            ]}
          />
          <Bar
            dataKey="alerts"
            radius={[3, 3, 0, 0]}
            // colour each bar by scan status
            fill="#3b82f6"
            // Override per-cell via Cell trick is complex; use a single colour
            // and rely on tooltip to show status. Clean and readable.
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
