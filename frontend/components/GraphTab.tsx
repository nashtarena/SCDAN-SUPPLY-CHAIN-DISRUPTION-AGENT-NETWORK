"use client";

import dynamic from "next/dynamic";
import AddNodeForm from "@/components/AddNodeForm";
import AlertFeed from "@/components/AlertFeed";
import type { Alert, SupplyChainDetail, SupplyChainEdge, SupplyChainNode } from "@/lib/types";

const SupplyChainGraph = dynamic(() => import("@/components/SupplyChainGraph"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center text-sm text-gray-500">
      Loading graph…
    </div>
  ),
});

interface Props {
  supplyChain: SupplyChainDetail;
  alerts: Alert[];
  onNodeAdded: (node: SupplyChainNode) => void;
  onEdgeAdded: (edge: SupplyChainEdge) => void;
}

export default function GraphTab({ supplyChain, alerts, onNodeAdded, onEdgeAdded }: Props) {
  return (
    <div className="flex flex-1 overflow-hidden">
      <div className="flex-1">
        <div className="relative h-full w-full">
          <SupplyChainGraph supplyChain={supplyChain} alerts={alerts} />
        </div>
      </div>
      <div className="flex w-72 shrink-0 flex-col gap-3 overflow-y-auto border-l border-border p-3">
        <AddNodeForm
          supplyChainId={supplyChain.id}
          nodes={supplyChain.nodes}
          onNodeAdded={onNodeAdded}
          onEdgeAdded={onEdgeAdded}
        />
        <div className="flex-1 overflow-hidden">
          <AlertFeed alerts={alerts} />
        </div>
      </div>
    </div>
  );
}
