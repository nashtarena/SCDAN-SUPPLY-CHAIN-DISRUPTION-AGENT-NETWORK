import type { Alert } from "./types";

export type Severity = "critical" | "high" | "medium" | "low" | "none";

const SEVERITY_RANK: Record<string, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
  none: 0,
};

export const SEVERITY_COLORS: Record<Severity, string> = {
  critical: "#ef4444",
  high:     "#f97316",
  medium:   "#eab308",
  low:      "#22c55e",
  none:     "#3b82f6",
};

export const SEVERITY_BG: Record<Severity, string> = {
  critical: "rgba(239,68,68,0.15)",
  high:     "rgba(249,115,22,0.15)",
  medium:   "rgba(234,179,8,0.15)",
  low:      "rgba(34,197,94,0.15)",
  none:     "rgba(59,130,246,0.10)",
};

/** Build a map of nodeId -> highest severity from the current alert list. */
export function buildNodeSeverityMap(alerts: Alert[]): Record<string, Severity> {
  const map: Record<string, Severity> = {};
  for (const alert of alerts) {
    if (!alert.node_id) continue;
    const current = SEVERITY_RANK[map[alert.node_id] ?? "none"] ?? 0;
    if ((SEVERITY_RANK[alert.severity] ?? 0) > current) {
      map[alert.node_id] = alert.severity as Severity;
    }
  }
  return map;
}
