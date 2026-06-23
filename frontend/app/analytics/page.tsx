"use client";

import Navbar from "@/components/Navbar";
import StatCard from "@/components/analytics/StatCard";
import SeverityPie from "@/components/analytics/SeverityPie";
import ScanStatusBar from "@/components/analytics/ScanStatusBar";
import TopRegionsBar from "@/components/analytics/TopRegionsBar";
import ExecutiveSummaryCard from "@/components/analytics/ExecutiveSummaryCard";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { useGlobalAnalytics, useGlobalSummary } from "@/lib/useAnalytics";

export default function AnalyticsPage() {
  const ready = useRequireAuth();
  const { data, loading, error } = useGlobalAnalytics();
  const { data: summary, loading: summaryLoading, refresh } = useGlobalSummary();

  if (!ready) return null;

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <div className="mx-auto max-w-6xl px-6 py-8 space-y-6">
        <h1 className="text-lg font-semibold text-white">Analytics</h1>

        {error && <p className="text-sm text-red-400">{error}</p>}

        {/* stat cards */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Total alerts"      value={data?.total_alerts ?? "—"} color="text-red-400" />
          <StatCard label="Supply chains"     value={data?.total_supply_chains ?? "—"} />
          <StatCard label="Scans completed"   value={data?.scan_status_breakdown.completed ?? "—"} color="text-green-400" />
          <StatCard label="Scans failed"      value={data?.scan_status_breakdown.failed ?? "—"} color="text-red-400" />
        </div>

        {/* executive summary */}
        <ExecutiveSummaryCard
          summary={summary?.summary ?? null}
          cached={summary?.cached ?? false}
          loading={summaryLoading}
          onRefresh={refresh}
        />

        {/* charts */}
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-64 animate-pulse rounded-lg border border-border bg-surface" />
            ))}
          </div>
        ) : data ? (
          <div className="grid gap-4 sm:grid-cols-3">
            <SeverityPie  data={data.severity_breakdown} />
            <ScanStatusBar data={data.scan_status_breakdown} />
            <TopRegionsBar data={data.top_regions} />
          </div>
        ) : null}
      </div>
    </div>
  );
}
