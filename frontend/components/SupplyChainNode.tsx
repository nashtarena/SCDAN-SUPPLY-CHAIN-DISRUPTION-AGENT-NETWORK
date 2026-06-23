"use client";

import { Handle, Position } from "reactflow";
import { SEVERITY_BG, SEVERITY_COLORS, type Severity } from "@/lib/severity";

export interface SupplyChainNodeData {
  label: string;
  type: string;
  region: string;
  severity: Severity;
}

export default function SupplyChainNode({ data }: { data: SupplyChainNodeData }) {
  const color = SEVERITY_COLORS[data.severity];
  const bg = SEVERITY_BG[data.severity];

  return (
    <>
      <Handle type="target" position={Position.Top} style={{ background: color }} />
      <div
        style={{ borderColor: color, backgroundColor: bg }}
        className="rounded-lg border px-4 py-2 text-center shadow-sm"
      >
        <p className="text-xs font-medium text-white">{data.label}</p>
        <p className="text-[10px] text-gray-400">{data.type}</p>
        <p className="text-[10px] text-gray-500">{data.region}</p>
        {data.severity !== "none" && (
          <span
            style={{ color }}
            className="mt-1 inline-block text-[9px] font-semibold uppercase tracking-wider"
          >
            {data.severity}
          </span>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} style={{ background: color }} />
    </>
  );
}
