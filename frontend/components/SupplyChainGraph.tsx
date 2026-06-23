"use client";

import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  type Node,
  type Edge,
  type Connection,
} from "reactflow";
import "reactflow/dist/style.css";
import { useCallback, useEffect, useMemo } from "react";
import SupplyChainNodeComponent from "./SupplyChainNode";
import {
  buildNodeSeverityMap,
  SEVERITY_COLORS,
  type Severity,
} from "@/lib/severity";
import type { Alert, SupplyChainDetail } from "@/lib/types";

const NODE_TYPES = { supplyChainNode: SupplyChainNodeComponent };

function layoutNodes(backendNodes: SupplyChainDetail["nodes"]): Node[] {
  return backendNodes.map((n, i) => ({
    id: n.id,
    type: "supplyChainNode",
    position:
      n.latitude != null && n.longitude != null
        ? { x: (n.longitude + 180) * 3, y: (90 - n.latitude) * 3 }
        : { x: (i % 4) * 240, y: Math.floor(i / 4) * 160 },
    data: {
      label: n.name,
      type: n.type,
      region: n.region,
      severity: "none" as Severity,
    },
  }));
}

function toFlowEdges(backendEdges: SupplyChainDetail["edges"]): Edge[] {
  return backendEdges.map((e) => ({
    id: e.id,
    source: e.source_node_id,
    target: e.target_node_id,
    label: e.transport_mode ?? undefined,
    style: { stroke: "#374151" },
    labelStyle: { fill: "#9ca3af", fontSize: 10 },
  }));
}

interface Props {
  supplyChain: SupplyChainDetail;
  alerts: Alert[];
}

export default function SupplyChainGraph({ supplyChain, alerts }: Props) {
  const severityMap = useMemo(() => buildNodeSeverityMap(alerts), [alerts]);

  const initialNodes = useMemo(
    () => layoutNodes(supplyChain.nodes),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [supplyChain.id]   // only re-layout when supply chain changes, not on every alert update
  );
  const initialEdges = useMemo(
    () => toFlowEdges(supplyChain.edges),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [supplyChain.id]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Re-apply severity colors whenever alerts change, without re-laying out.
  useEffect(() => {
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          severity: (severityMap[n.id] ?? "none") as Severity,
        },
      }))
    );
  }, [severityMap, setNodes]);

  // Sync new nodes/edges added via the AddNodeForm.
  useEffect(() => {
    setNodes(layoutNodes(supplyChain.nodes));
  }, [supplyChain.nodes.length, setNodes]);

  useEffect(() => {
    setEdges(toFlowEdges(supplyChain.edges));
  }, [supplyChain.edges.length, setEdges]);

  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    [setEdges]
  );

  return (
    // BUG FIX: absolute inset-0 fills the positioned parent (relative h-full w-full)
    // completely. This guarantees ReactFlow always has a real pixel box to render into.
    <div className="absolute inset-0">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={NODE_TYPES}
        fitView
        attributionPosition="bottom-right"
        style={{ background: "#0b0f14" }}
      >
        <Background color="#1f2937" gap={20} />
        <Controls />
        <MiniMap
          nodeColor={(n) =>
            SEVERITY_COLORS[(n.data?.severity as Severity) ?? "none"]
          }
          style={{ background: "#121821" }}
        />
      </ReactFlow>
    </div>
  );
}
