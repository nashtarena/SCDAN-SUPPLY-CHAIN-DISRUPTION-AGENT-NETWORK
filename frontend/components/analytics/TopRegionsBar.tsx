"use client";

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import type { RegionStat } from "@/lib/types";

interface Props {
  data: RegionStat[];
  title?: string;
}

export default function TopRegionsBar({ data, title = "Top affected regions" }: Props) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <p className="mb-3 text-sm font-medium text-white">{title}</p>
      {data.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-500">No data yet</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 0, right: 16, left: 8, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fill: "#9ca3af", fontSize: 11 }}
              allowDecimals={false}
            />
            <YAxis
              type="category"
              dataKey="region"
              width={110}
              tick={{ fill: "#9ca3af", fontSize: 11 }}
            />
            <Tooltip
              contentStyle={{ background: "#121821", border: "1px solid #22293580", borderRadius: 6 }}
              labelStyle={{ color: "#e5e7eb" }}
              itemStyle={{ color: "#9ca3af" }}
            />
            <Bar dataKey="count" fill="#3b82f6" radius={[0, 3, 3, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
