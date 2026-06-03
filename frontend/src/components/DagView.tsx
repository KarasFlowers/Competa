import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "@dagrejs/dagre";
import { dagApi, type DagStructure, type DagNode, type SSEEvent } from "../api/client";
import { CheckCircle, XCircle, Clock, Loader2, AlertTriangle } from "lucide-react";

// ---------------------------------------------------------------------------
// Dagre auto-layout
// ---------------------------------------------------------------------------

const NODE_WIDTH = 180;
const NODE_HEIGHT = 56;

function layoutWithDagre(nodes: Node[], edges: Edge[]): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 60, ranksep: 100 });

  for (const n of nodes) {
    g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const e of edges) {
    g.setEdge(e.source, e.target);
  }

  dagre.layout(g);

  const layoutedNodes = nodes.map((n) => {
    const pos = g.node(n.id);
    return {
      ...n,
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 },
    };
  });

  return { nodes: layoutedNodes, edges };
}

// ---------------------------------------------------------------------------
// Status → style mapping
// ---------------------------------------------------------------------------

const STATUS_STYLES: Record<string, { bg: string; border: string; text: string; icon: string }> = {
  pending: {
    bg: "bg-gray-50",
    border: "border-gray-200",
    text: "text-gray-400",
    icon: "text-gray-300",
  },
  running: {
    bg: "bg-blue-50",
    border: "border-blue-300",
    text: "text-blue-700",
    icon: "text-blue-500",
  },
  completed: {
    bg: "bg-green-50",
    border: "border-green-300",
    text: "text-green-700",
    icon: "text-green-500",
  },
  failed: {
    bg: "bg-red-50",
    border: "border-red-300",
    text: "text-red-700",
    icon: "text-red-500",
  },
};

function StatusIcon({ status }: { status: string }) {
  const cls = STATUS_STYLES[status]?.icon ?? "text-gray-300";
  switch (status) {
    case "running":
      return <Loader2 className={`w-4 h-4 ${cls} animate-spin`} />;
    case "completed":
      return <CheckCircle className={`w-4 h-4 ${cls}`} />;
    case "failed":
      return <XCircle className={`w-4 h-4 ${cls}`} />;
    default:
      return <Clock className={`w-4 h-4 ${cls}`} />;
  }
}

// ---------------------------------------------------------------------------
// Custom node component
// ---------------------------------------------------------------------------

function AgentNode({ data }: { data: Node["data"] & { label: string; nodeType: string; status: string } }) {
  const style = STATUS_STYLES[data.status] ?? STATUS_STYLES.pending;
  return (
    <>
      <Handle type="target" position={Position.Left} className="w-2 h-2 opacity-0" />
      <div
        className={`px-4 py-3 rounded-xl border-2 shadow-sm flex items-center gap-3 min-w-[160px] h-full transition-all ${style.bg} ${style.border}`}
      >
        <StatusIcon status={data.status} />
        <div className="flex flex-col">
          <span className={`text-sm font-semibold ${style.text}`}>{data.label}</span>
          <span className="text-[10px] text-gray-400 uppercase tracking-wider">
            {data.nodeType === "tool" ? "工具" : "Agent"}
          </span>
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="w-2 h-2 opacity-0" />
    </>
  );
}

const nodeTypes = { agentNode: AgentNode };

// ---------------------------------------------------------------------------
// Convert API data → React Flow elements
// ---------------------------------------------------------------------------

function toFlowElements(dag: DagStructure) {
  const nodes: Node[] = dag.nodes.map((n: DagNode) => ({
    id: n.id,
    type: "agentNode",
    position: { x: 0, y: 0 },
    data: { label: n.label, nodeType: n.type, status: n.status },
  }));

  const edges: Edge[] = dag.edges.map((e, i) => ({
    id: `e-${e.source}-${e.target}-${i}`,
    source: e.source,
    target: e.target,
    label: e.label ?? undefined,
    style: e.label === "retry" ? { stroke: "#f59e0b", strokeDasharray: "6 3" } : undefined,
    animated: e.label === "retry",
    type: "smoothstep",
  }));

  return layoutWithDagre(nodes, edges);
}

// ---------------------------------------------------------------------------
// DagView component
// ---------------------------------------------------------------------------

interface DagViewProps {
  taskId: string;
  onNodeClick?: (nodeId: string) => void;
  height?: string;
}

export default function DagView({ taskId, onNodeClick, height = "320px" }: DagViewProps) {
  const [dag, setDag] = useState<DagStructure | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch DAG data
  useEffect(() => {
    let cancelled = false;
    const fetchDag = async () => {
      try {
        const { data } = await dagApi.get(taskId);
        if (!cancelled) setDag(data);
      } catch (err) {
        console.error("Failed to load DAG", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchDag();
    return () => { cancelled = true; };
  }, [taskId]);

  // SSE real-time updates
  useEffect(() => {
    const es = new EventSource(`/api/tasks/${taskId}/events`);
    es.addEventListener("progress", (e) => {
      try {
        const evt: SSEEvent = JSON.parse((e as MessageEvent).data);
        setDag((prev) => {
          if (!prev) return prev;
          const agentName = evt.agent;
          const newStatus = evt.status;
          if (!agentName || !newStatus) return prev;
          return {
            ...prev,
            nodes: prev.nodes.map((n) =>
              n.id === agentName ? { ...n, status: newStatus } : n
            ),
          };
        });
      } catch { /* ignore parse errors */ }
    });
    return () => es.close();
  }, [taskId]);

  // Build React Flow elements
  const { initialNodes, initialEdges } = useMemo(() => {
    if (!dag) return { initialNodes: [], initialEdges: [] };
    const { nodes, edges } = toFlowElements(dag);
    return { initialNodes: nodes, initialEdges: edges };
  }, [dag]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Sync when dag changes
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      onNodeClick?.(node.id);
    },
    [onNodeClick]
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8 text-gray-400">
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        加载DAG结构中...
      </div>
    );
  }

  if (!dag) {
    return (
      <div className="flex items-center justify-center py-8 text-gray-400">
        <AlertTriangle className="w-5 h-5 mr-2" />
        无法加载DAG结构
      </div>
    );
  }

  return (
    <div style={{ height, width: "100%" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        proOptions={{ hideAttribution: true }}
        minZoom={0.3}
        maxZoom={1.5}
        nodesDraggable={false}
        nodesConnectable={false}
      >
        <Background color="#e5e7eb" gap={16} />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={(n) => {
            const s = n.data?.status as string;
            if (s === "running") return "#3b82f6";
            if (s === "completed") return "#22c55e";
            if (s === "failed") return "#ef4444";
            return "#d1d5db";
          }}
          maskColor="rgba(0,0,0,0.05)"
        />
      </ReactFlow>
    </div>
  );
}
