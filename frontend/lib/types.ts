export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
}

export interface SupplyChain {
  id: string;
  owner_id: string;
  name: string;
  description: string | null;
}

export interface SupplyChainNode {
  id: string;
  supply_chain_id: string;
  name: string;
  type: string;
  region: string;
  latitude: number | null;
  longitude: number | null;
}

export interface SupplyChainEdge {
  id: string;
  supply_chain_id: string;
  source_node_id: string;
  target_node_id: string;
  transport_mode: string | null;
}

export interface SupplyChainDetail extends SupplyChain {
  nodes: SupplyChainNode[];
  edges: SupplyChainEdge[];
}

export interface ScanQueued {
  scan_result_id: string;
  status: string;
}

export interface ScanResult {
  id: string;
  supply_chain_id: string;
  status: "pending" | "running" | "completed" | "failed";
  started_at: string | null;
  completed_at: string | null;
  timing: Record<string, number> | null;
  error_message: string | null;
}

export interface Alert {
  id: string;
  scan_result_id: string;
  supply_chain_id: string;
  node_id: string | null;
  severity: "low" | "medium" | "high" | "critical";
  category: string;
  region: string;
  message: string;
  created_at: string;
}

// ── Analytics ──────────────────────────────────────────────────────────────

export interface SeverityBreakdown {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface ScanStatusBreakdown {
  completed: number;
  failed: number;
  running: number;
  pending: number;
}

export interface RegionStat {
  region: string;
  count: number;
}

export interface ScanHistoryEntry {
  scan_id: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  alert_count: number;
  timing: Record<string, number> | null;
}

export interface GlobalAnalytics {
  total_alerts: number;
  severity_breakdown: SeverityBreakdown;
  scan_status_breakdown: ScanStatusBreakdown;
  top_regions: RegionStat[];
  total_supply_chains: number;
}

export interface ChainAnalytics {
  total_alerts: number;
  severity_breakdown: SeverityBreakdown;
  top_regions: RegionStat[];
  scan_history: ScanHistoryEntry[];
}

export interface ExecutiveSummary {
  summary: string;
  cached: boolean;
}