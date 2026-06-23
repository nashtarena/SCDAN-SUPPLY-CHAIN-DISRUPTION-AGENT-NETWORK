"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";
import type { Alert, ScanResult, SupplyChainDetail, SupplyChainEdge, SupplyChainNode } from "@/lib/types";
import Navbar from "@/components/Navbar";
import ScanStatus from "@/components/ScanStatus";
import GraphTab from "@/components/GraphTab";
import AnalyticsTab from "@/components/analytics/AnalyticsTab";

type Tab = "graph" | "analytics";

const ALERT_POLL_MS = 5_000;
const SCAN_POLL_MS  = 3_000;

export default function SupplyChainPage() {
  const ready = useRequireAuth();
  const { id } = useParams<{ id: string }>();

  const [supplyChain, setSupplyChain] = useState<SupplyChainDetail | null>(null);
  const [alerts, setAlerts]           = useState<Alert[]>([]);
  const [scan, setScan]               = useState<ScanResult | null>(null);
  const [scanning, setScanning]       = useState(false);
  const [tab, setTab]                 = useState<Tab>("graph");
  const [pageError, setPageError]     = useState<string | null>(null);

  const scanPollRef  = useRef<ReturnType<typeof setInterval> | null>(null);
  const alertPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!ready || !id) return;
    loadSupplyChain();
    loadAlerts();
    alertPollRef.current = setInterval(loadAlerts, ALERT_POLL_MS);
    return () => {
      if (alertPollRef.current) clearInterval(alertPollRef.current);
      if (scanPollRef.current)  clearInterval(scanPollRef.current);
    };
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
    } catch {}
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

  async function handleRunScan() {
    if (!id || scanning) return;
    setScanning(true);
    setScan(null);
    try {
      const res = await api.post<{ scan_result_id: string }>("/api/scans", { supply_chain_id: id });
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

  const tabCls = (t: Tab) =>
    `px-4 py-2 text-sm font-medium border-b-2 transition ${
      tab === t
        ? "border-primary text-white"
        : "border-transparent text-gray-400 hover:text-white"
    }`;

  return (
    <div className="flex h-screen flex-col bg-background">
      <Navbar />

      {/* header */}
      <div className="shrink-0 border-b border-border bg-surface px-6 pt-3">
        <div className="flex items-center justify-between pb-2">
          <div>
            <h1 className="font-semibold text-white">{supplyChain.name}</h1>
            {supplyChain.description && (
              <p className="text-xs text-gray-400">{supplyChain.description}</p>
            )}
          </div>
          <ScanStatus scan={scan} onRunScan={handleRunScan} scanning={scanning} />
        </div>

        {/* tab bar sits flush with the header bottom border */}
        <div className="flex gap-0">
          <button className={tabCls("graph")}     onClick={() => setTab("graph")}>Graph</button>
          <button className={tabCls("analytics")} onClick={() => setTab("analytics")}>Analytics</button>
        </div>
      </div>

      {/* body — graph tab needs overflow-hidden + full height; analytics is scrollable */}
      {tab === "graph" ? (
        <GraphTab
          supplyChain={supplyChain}
          alerts={alerts}
          onNodeAdded={handleNodeAdded}
          onEdgeAdded={handleEdgeAdded}
        />
      ) : (
        <AnalyticsTab supplyChainId={id} />
      )}
    </div>
  );
}
