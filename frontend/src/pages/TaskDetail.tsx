import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { taskApi, metricsApi, type Task, type Metrics } from "../api/client";

const ACTIVE_STATUSES = new Set([
  "collecting",
  "analyzing",
  "writing",
  "filtering",
  "qa",
  "retrying",
]);

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  collecting: "bg-blue-100 text-blue-700",
  analyzing: "bg-indigo-100 text-indigo-700",
  writing: "bg-purple-100 text-purple-700",
  filtering: "bg-yellow-100 text-yellow-700",
  qa: "bg-orange-100 text-orange-700",
  retrying: "bg-amber-100 text-amber-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>();
  const [task, setTask] = useState<Task | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    taskApi.get(id).then((r) => {
      setTask(r.data);
      setPolling(ACTIVE_STATUSES.has(r.data.status));
      if (ACTIVE_STATUSES.has(r.data.status)) {
        setMetrics(null);
      }
    }).catch(() => setError("Task not found"));
    metricsApi.get(id).then((r) => setMetrics(r.data)).catch(() => {});
  }, [id]);

  // Poll status while running
  useEffect(() => {
    if (!id || !polling) return;
    const interval = setInterval(async () => {
      try {
        const r = await taskApi.getStatus(id);
        setTask((prev) => (prev ? { ...prev, status: r.data.status } : prev));
        if (["completed", "failed"].includes(r.data.status)) {
          setPolling(false);
          metricsApi.get(id).then((r) => setMetrics(r.data)).catch(() => {});
        }
      } catch {}
    }, 2000);
    return () => clearInterval(interval);
  }, [id, polling]);

  const handleRun = async () => {
    if (!id) return;
    try {
      setError("");
      await taskApi.run(id);
      setMetrics(null);
      setPolling(true);
      setTask((prev) => (prev ? { ...prev, status: "collecting" } : prev));
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to start pipeline");
    }
  };

  if (error) return <div className="p-8 text-red-600">{error}</div>;
  if (!task) return <div className="p-8 text-gray-500">Loading...</div>;

  const statusClass = STATUS_COLORS[task.status] || "bg-gray-100 text-gray-700";

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{task.target_product}</h1>
          <p className="text-sm text-gray-500 mt-1">
            {task.industry || "No industry"} &middot; {task.competitors.length} competitors
          </p>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusClass}`}>
          {task.status}
        </span>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        {["pending", "failed", "completed"].includes(task.status) && (
          <button
            onClick={handleRun}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Run Pipeline
          </button>
        )}
        {task.status === "completed" && (
          <Link
            to={`/tasks/${id}/report`}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
          >
            View Report
          </Link>
        )}
      </div>

      {/* Competitors */}
      <section>
        <h2 className="text-lg font-semibold text-gray-800 mb-2">Competitors</h2>
        <div className="flex flex-wrap gap-2">
          {task.competitors.map((c, i) => (
            <span key={i} className="px-3 py-1 bg-gray-100 rounded-full text-sm text-gray-700">{c}</span>
          ))}
          {task.competitors.length === 0 && (
            <span className="text-sm text-gray-400">None specified</span>
          )}
        </div>
      </section>

      {/* Metrics */}
      {metrics && (
        <section>
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Quality Metrics</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard label="Sources" value={metrics.source_count} />
            <MetricCard label="Claims" value={metrics.claim_count} />
            <MetricCard label="Evidence Coverage" value={`${(metrics.evidence_coverage_rate * 100).toFixed(1)}%`} />
            <MetricCard label="Manual Corrections" value={metrics.manual_correction_count} />
          </div>
        </section>
      )}

      {/* Polling indicator */}
      {polling && (
        <div className="flex items-center gap-2 text-blue-600 text-sm">
          <span className="animate-spin inline-block w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full" />
          Pipeline running... status updates every 2s
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 text-center">
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  );
}
