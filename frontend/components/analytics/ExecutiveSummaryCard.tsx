"use client";

interface Props {
  summary: string | null;
  cached: boolean;
  loading: boolean;
  onRefresh: () => void;
}

export default function ExecutiveSummaryCard({ summary, cached, loading, onRefresh }: Props) {
  return (
    <div className="rounded-lg border border-border bg-surface p-5">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-white">Executive Summary</p>
          {cached && !loading && (
            <p className="text-[10px] text-gray-500">Cached · 24h refresh</p>
          )}
        </div>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="rounded-md border border-border px-3 py-1 text-xs text-gray-400 transition hover:text-white disabled:opacity-40"
        >
          {loading ? "Generating…" : "↻ Refresh"}
        </button>
      </div>

      {loading ? (
        <div className="space-y-2">
          <div className="h-3 w-full animate-pulse rounded bg-white/5" />
          <div className="h-3 w-5/6 animate-pulse rounded bg-white/5" />
          <div className="h-3 w-4/6 animate-pulse rounded bg-white/5" />
        </div>
      ) : summary ? (
        <p className="text-sm leading-relaxed text-gray-300">{summary}</p>
      ) : (
        <p className="text-sm text-gray-500">No summary available.</p>
      )}
    </div>
  );
}
