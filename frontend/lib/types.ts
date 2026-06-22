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
