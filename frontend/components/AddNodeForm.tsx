"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { SupplyChainNode, SupplyChainEdge, SupplyChainDetail } from "@/lib/types";

const NODE_TYPES = ["supplier", "factory", "port", "warehouse", "distributor"];

interface Props {
  supplyChainId: string;
  nodes: SupplyChainNode[];
  onNodeAdded: (node: SupplyChainNode) => void;
  onEdgeAdded: (edge: SupplyChainEdge) => void;
}

export default function AddNodeForm({ supplyChainId, nodes, onNodeAdded, onEdgeAdded }: Props) {
  const [tab, setTab] = useState<"node" | "edge">("node");

  // Node form state
  const [name, setName] = useState("");
  const [type, setType] = useState("port");
  const [region, setRegion] = useState("");
  const [nodeLoading, setNodeLoading] = useState(false);
  const [nodeError, setNodeError] = useState<string | null>(null);

  // Edge form state
  const [sourceId, setSourceId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [transportMode, setTransportMode] = useState("ship");
  const [edgeLoading, setEdgeLoading] = useState(false);
  const [edgeError, setEdgeError] = useState<string | null>(null);

  async function handleAddNode(e: React.FormEvent) {
    e.preventDefault();
    setNodeError(null);
    setNodeLoading(true);
    try {
      const res = await api.post<SupplyChainNode>(
        `/api/supply-chains/${supplyChainId}/nodes`,
        { name, type, region }
      );
      onNodeAdded(res.data);
      setName("");
      setRegion("");
    } catch (err: any) {
      setNodeError(err?.response?.data?.detail ?? "Failed to add node.");
    } finally {
      setNodeLoading(false);
    }
  }

  async function handleAddEdge(e: React.FormEvent) {
    e.preventDefault();
    setEdgeError(null);
    setEdgeLoading(true);
    try {
      const res = await api.post<SupplyChainEdge>(
        `/api/supply-chains/${supplyChainId}/edges`,
        {
          source_node_id: sourceId,
          target_node_id: targetId,
          transport_mode: transportMode || null,
        }
      );
      onEdgeAdded(res.data);
      setSourceId("");
      setTargetId("");
    } catch (err: any) {
      setEdgeError(err?.response?.data?.detail ?? "Failed to add edge.");
    } finally {
      setEdgeLoading(false);
    }
  }

  const inputCls =
    "w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm text-white outline-none focus:border-primary";
  const tabCls = (active: boolean) =>
    `px-3 py-1.5 text-xs font-medium rounded-md transition ${
      active ? "bg-primary text-white" : "text-gray-400 hover:text-white"
    }`;

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="mb-4 flex gap-2">
        <button className={tabCls(tab === "node")} onClick={() => setTab("node")}>+ Node</button>
        <button className={tabCls(tab === "edge")} onClick={() => setTab("edge")}>+ Edge</button>
      </div>

      {tab === "node" && (
        <form onSubmit={handleAddNode} className="space-y-2">
          <input required value={name} onChange={(e) => setName(e.target.value)}
            placeholder="Node name" className={inputCls} />
          <select value={type} onChange={(e) => setType(e.target.value)} className={inputCls}>
            {NODE_TYPES.map((t) => <option key={t}>{t}</option>)}
          </select>
          <input required value={region} onChange={(e) => setRegion(e.target.value)}
            placeholder="Region (e.g. Shanghai, CN)" className={inputCls} />
          {nodeError && <p className="text-xs text-red-400">{nodeError}</p>}
          <button type="submit" disabled={nodeLoading}
            className="w-full rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">
            {nodeLoading ? "Adding…" : "Add node"}
          </button>
        </form>
      )}

      {tab === "edge" && (
        <form onSubmit={handleAddEdge} className="space-y-2">
          <select required value={sourceId} onChange={(e) => setSourceId(e.target.value)} className={inputCls}>
            <option value="">Source node…</option>
            {nodes.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
          </select>
          <select required value={targetId} onChange={(e) => setTargetId(e.target.value)} className={inputCls}>
            <option value="">Target node…</option>
            {nodes.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
          </select>
          <select value={transportMode} onChange={(e) => setTransportMode(e.target.value)} className={inputCls}>
            {["ship", "truck", "rail", "air"].map((m) => <option key={m}>{m}</option>)}
          </select>
          {edgeError && <p className="text-xs text-red-400">{edgeError}</p>}
          <button type="submit" disabled={edgeLoading}
            className="w-full rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">
            {edgeLoading ? "Adding…" : "Add edge"}
          </button>
        </form>
      )}
    </div>
  );
}
