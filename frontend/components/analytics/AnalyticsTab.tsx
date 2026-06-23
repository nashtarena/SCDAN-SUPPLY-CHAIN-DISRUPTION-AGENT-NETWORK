"use client";

import { useChainAnalytics, useChainSummary } from "@/lib/useAnalytics";
import StatCard from "@/components/analytics/StatCard";
import SeverityPie from "@/components/analytics/SeverityPie";
import TopRegionsBar from "@/components/analytics/TopRegionsBar";
import ScanHistoryBar from "@/components/analytics/ScanHistoryBar";
import ExecutiveSummaryCard from "@/components/analytics/ExecutiveSummaryCard";

interface Props {
  supplyChainId: string;
}

export default function AnalyticsTab({ supplyChainId }: Props) {
  const { data, loading, error } = useChainAnalytics(supplyChainId);
  const { data: summary, loading: summaryLoading, refresh } = useChainSummary(supplyChainId);

  const completedScans = data?.scan_history.filter((s) => s.status === "completed").length ?? 0;
  const failedScans    = data?.scan_history.filter((s) => s.status === "failed").length ?? 0;

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-5xl space-y-5 p-6">

        {error && <p className="text-sm text-red-400">{error}</p>}

        {/* stat cards */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Total alerts"    value={data?.total_alerts ?? "—"} color="text-red-400" />
          <StatCard label="Critical"        value={data?.severity_breakdown.critical ?? "—"} color="text-red-400" />
          <StatCard label="Scans completed" value={completedScans} color="text-green-400" />
          <StatCard label="Scans failed"    value={failedScans}    color="text-red-400" />
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
          <>
            <div className="grid gap-4 sm:grid-cols-2">
              <SeverityPie  data={data.severity_breakdown} />
              <TopRegionsBar data={data.top_regions} />
            </div>
            <ScanHistoryBar data={data.scan_history} />
          </>
        ) : null}

      </div>
    </div>
  );
}
