"use client";

import type { ScanResult } from "@/lib/types";

interface Props {
  scan: ScanResult | null;
  onRunScan: () => void;
  scanning: boolean;
}

const STATUS_LABEL: Record<string, string> = {
  pending: "Queued…",
  running: "Running agents…",
  completed: "Completed",
  failed: "Failed",
};

const STATUS_COLOR: Record<string, string> = {
  pending: "text-yellow-400",
  running: "text-blue-400",
  completed: "text-green-400",
  failed: "text-red-400",
};

export default function ScanStatus({ scan, onRunScan, scanning }: Props) {
  const isActive =
    scan?.status === "pending" || scan?.status === "running";

  return (
    <div className="flex items-center gap-4">
      {scan && (
        <div className="flex items-center gap-2">
          {isActive && (
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-blue-400" />
          )}
          <span className={`text-sm font-medium ${STATUS_COLOR[scan.status] ?? "text-gray-400"}`}>
            {STATUS_LABEL[scan.status] ?? scan.status}
          </span>
          {scan.timing && (
            <span className="text-xs text-gray-500">
              ({Object.entries(scan.timing)
                .map(([k, v]) => `${k.replace("_seconds", "")}: ${v}s`)
                .join(" · ")})
            </span>
          )}
          {scan.error_message && (
            <span className="text-xs text-red-400" title={scan.error_message}>
              — {scan.error_message.slice(0, 60)}
            </span>
          )}
        </div>
      )}

      <button
        onClick={onRunScan}
        disabled={scanning || isActive}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-40"
      >
        {isActive ? "Scanning…" : "Run Scan"}
      </button>
    </div>
  );
}
