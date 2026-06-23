"use client";

import type { Alert } from "@/lib/types";
import { SEVERITY_COLORS } from "@/lib/severity";

interface Props {
  alerts: Alert[];
}

const SEVERITY_LABEL: Record<string, string> = {
  critical: "CRITICAL",
  high: "HIGH",
  medium: "MED",
  low: "LOW",
};

export default function AlertFeed({ alerts }: Props) {
  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-surface">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-white">
          Alerts
          {alerts.length > 0 && (
            <span className="ml-2 rounded-full bg-red-500/20 px-2 py-0.5 text-xs text-red-400">
              {alerts.length}
            </span>
          )}
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto">
        {alerts.length === 0 ? (
          <p className="px-4 py-6 text-sm text-gray-500">No alerts yet. Run a scan to detect disruptions.</p>
        ) : (
          <ul className="divide-y divide-border">
            {alerts.map((alert) => (
              <li key={alert.id} className="px-4 py-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-white">{alert.message}</p>
                    <p className="mt-0.5 text-xs text-gray-400">
                      {alert.region} · {alert.category}
                    </p>
                    <p className="mt-0.5 text-[10px] text-gray-600">
                      {new Date(alert.created_at).toLocaleString()}
                    </p>
                  </div>
                  <span
                    style={{ color: SEVERITY_COLORS[alert.severity] }}
                    className="shrink-0 text-[10px] font-bold uppercase tracking-wider"
                  >
                    {SEVERITY_LABEL[alert.severity] ?? alert.severity}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
