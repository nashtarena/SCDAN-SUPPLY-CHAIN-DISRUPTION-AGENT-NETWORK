"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";
import type {
  Alert,
  ScanResult,
  SupplyChainDetail,
  SupplyChainEdge,
  SupplyChainNode,
} from "@/lib/types";
import Navbar from "@/components/Navbar";
import ScanStatus from "@/components/ScanStatus";
import AlertFeed from "@/components/AlertFeed";
import AddNodeForm from "@/components/AddNodeForm";
import dynamic from "next/dynamic";

// ReactFlow must be client-only (uses browser APIs).
const SupplyChainGraph = dynamic(() => import("@/components/SupplyChainGraph"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center text-sm text-gray-500">
      Loading graph…
    </div>
  ),
});

const ALERT_POLL_MS = 5_000;
const SCAN_POLL_MS  = 3_000;

export default function SupplyChainPage() {
  const ready = useRequireAuth();
  const { id } = useParams<{ id: string }>();

  const [supplyChain, setSupplyChain] = useState<SupplyChainDetail | null>(null);
  const [alerts, setAlerts]           = useState<Alert[]>([]);
  const [scan, setScan]               = useState<ScanResult | null>(null);
  const [scanning, setScanning]       = useState(false);
  const [pageError, setPageError]     = useState<string | null>(null);

  const scanPollRef  = useRef<ReturnType<typeof setInterval> | null>(null);
  const alertPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!ready || !id) return;
    loadSupplyChain();
    loadAlerts();
    startAlertPolling();
    return () => stopPolling();
  }, [ready, id]);

  async function loadSupplyChain() {
    try {
      const res = await api.get<SupplyChainDetail>(`/api/supply-chains/${id}`);
      setSupplyChain(res.data);
    } catch {
      setPageError("Could not load supply chain.");
    }
  }

  async function loadAlerts() {
    try {
      const res = await api.get<Alert[]>(`/api/alerts/${id}`);
      setAlerts(res.data);
    } catch {
      // Non-fatal.
    }
  }

  function startAlertPolling() {
    if (alertPollRef.current) clearInterval(alertPollRef.current);
    alertPollRef.current = setInterval(loadAlerts, ALERT_POLL_MS);
  }

  function stopAlertPolling() {
    if (alertPollRef.current) clearInterval(alertPollRef.current);
  }

  function startScanPolling(scanId: string) {
    if (scanPollRef.current) clearInterval(scanPollRef.current);
    scanPollRef.current = setInterval(async () => {
      try {
        const res = await api.get<ScanResult>(`/api/scans/${scanId}`);
        setScan(res.data);
        if (res.data.status === "completed" || res.data.status === "failed") {
          clearInterval(scanPollRef.current!);
          setScanning(false);
          await loadAlerts();
        }
      } catch {
        clearInterval(scanPollRef.current!);
        setScanning(false);
      }
    }, SCAN_POLL_MS);
  }

  function stopPolling() {
    stopAlertPolling();
    if (scanPollRef.current) clearInterval(scanPollRef.current);
  }

  async function handleRunScan() {
    if (!id || scanning) return;
    setScanning(true);
    setScan(null);
    try {
      const res = await api.post<{ scan_result_id: string }>("/api/scans", {
        supply_chain_id: id,
      });
      const scanRes = await api.get<ScanResult>(`/api/scans/${res.data.scan_result_id}`);
      setScan(scanRes.data);
      startScanPolling(res.data.scan_result_id);
    } catch (err: any) {
      setScanning(false);
      setPageError(err?.response?.data?.detail ?? "Failed to start scan.");
    }
  }

  function handleNodeAdded(node: SupplyChainNode) {
    setSupplyChain((sc) => sc ? { ...sc, nodes: [...sc.nodes, node] } : sc);
  }

  function handleEdgeAdded(edge: SupplyChainEdge) {
    setSupplyChain((sc) => sc ? { ...sc, edges: [...sc.edges, edge] } : sc);
  }

  if (!ready) return null;

  if (pageError) {
    return (
      <div className="flex h-screen flex-col bg-background">
        <Navbar />
        <div className="flex flex-1 items-center justify-center">
          <p className="text-sm text-red-400">{pageError}</p>
        </div>
      </div>
    );
  }

  if (!supplyChain) {
    return (
      <div className="flex h-screen flex-col bg-background">
        <Navbar />
        <div className="flex flex-1 items-center justify-center">
          <p className="text-sm text-gray-500">Loading…</p>
        </div>
      </div>
    );
  }

  return (
    // BUG FIX: h-screen (not min-h-screen) so flex-1 children get real pixel
    // heights. React Flow's h-full needs a concrete ancestor height to render.
    <div className="flex h-screen flex-col bg-background">
      <Navbar />

      {/* header */}
      <div className="flex shrink-0 items-center justify-between border-b border-border bg-surface px-6 py-3">
        <div>
          <h1 className="font-semibold text-white">{supplyChain.name}</h1>
          {supplyChain.description && (
            <p className="text-xs text-gray-400">{supplyChain.description}</p>
          )}
        </div>
        <ScanStatus scan={scan} onRunScan={handleRunScan} scanning={scanning} />
      </div>

      {/* body: graph + sidebar — flex-1 so they fill remaining screen height */}
      <div className="flex flex-1 overflow-hidden">
        {/* graph */}
        <div className="flex-1">
          {/* ReactFlow BUG FIX: needs an explicit pixel height on its direct
              wrapper, not just h-full, because "full" won't resolve when the
              ancestor is a flex container with dynamic height. We use 100% of
              the flex-1 parent via a positioned fill pattern. */}
          <div className="relative h-full w-full">
            <SupplyChainGraph supplyChain={supplyChain} alerts={alerts} />
          </div>
        </div>

        {/* sidebar */}
        <div className="flex w-72 shrink-0 flex-col gap-3 overflow-y-auto border-l border-border p-3">
          <AddNodeForm
            supplyChainId={id}
            nodes={supplyChain.nodes}
            onNodeAdded={handleNodeAdded}
            onEdgeAdded={handleEdgeAdded}
          />
          <div className="flex-1 overflow-hidden">
            <AlertFeed alerts={alerts} />
          </div>
        </div>
      </div>
    </div>
  );
}
