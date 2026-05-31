import { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { taskApi, metricsApi, type Task, type Metrics, type SSEEvent } from "../api/client";
import { useToast } from "../components/Toast";
import { Activity, Plus, RefreshCw } from "lucide-react";

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
  const { toast } = useToast();
  const [task, setTask] = useState<Task | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState("");
  const [sseEvent, setSseEvent] = useState<SSEEvent | null>(null);
  const [showSourceModal, setShowSourceModal] = useState(false);
  const [newSource, setNewSource] = useState({ title: "", url: "", content_snippet: "", type: "url" });
  
  const eventSourceRef = useRef<EventSource | null>(null);

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

  // Set up SSE when running
  useEffect(() => {
    if (!id || !polling) return;

    const setupSSE = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const source = new EventSource(`/api/tasks/${id}/events`);
      eventSourceRef.current = source;

      source.addEventListener("connected", () => {
        console.log("SSE Connected");
      });

      source.addEventListener("progress", (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.agent) {
            setSseEvent(data as SSEEvent);
          }
        } catch (e) {}
      });

      source.onerror = () => {
        source.close();
      };
    };

    setupSSE();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [id, polling]);

  // Fallback Polling (in case SSE fails/drops)
  useEffect(() => {
    if (!id || !polling) return;
    const interval = setInterval(async () => {
      try {
        const r = await taskApi.getStatus(id);
        setTask((prev) => (prev ? { ...prev, status: r.data.status } : prev));
        if (["completed", "failed"].includes(r.data.status)) {
          setPolling(false);
          setSseEvent(null);
          if (eventSourceRef.current) {
            eventSourceRef.current.close();
          }
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
      setSseEvent(null);
      setTask((prev) => (prev ? { ...prev, status: "collecting" } : prev));
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to start pipeline");
    }
  };

  const handleRerun = async () => {
    if (!id) return;
    try {
      setError("");
      await taskApi.rerun(id);
      setMetrics(null);
      setPolling(true);
      setSseEvent(null);
      setTask((prev) => (prev ? { ...prev, status: "collecting" } : prev));
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to restart pipeline");
    }
  };

  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    try {
      await taskApi.submitCorrection(id, {
        correction_type: "add_source",
        data: newSource,
      });
      setShowSourceModal(false);
      setNewSource({ title: "", url: "", content_snippet: "", type: "url" });
      // Suggest rerun
      toast("资料已补充！请点击「重新生成」以纳入新资料并修正报告。", "success");
    } catch (err) {
      toast("补充资料失败", "error");
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
          <div className="flex gap-3">
            <Link
              to={`/tasks/${id}/report`}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
            >
              查看报告
            </Link>
            <Link
              to={`/tasks/${id}/traces`}
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2 transition"
            >
              <Activity className="w-4 h-4" />
              执行追踪
            </Link>
            <button
              onClick={() => setShowSourceModal(true)}
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2 transition"
            >
              <Plus className="w-4 h-4" />
              补充资料
            </button>
            <button
              onClick={handleRerun}
              className="px-4 py-2 bg-white border border-blue-300 text-blue-700 rounded-lg hover:bg-blue-50 flex items-center gap-2 transition"
              title="保留现有资料和约束，重新生成报告"
            >
              <RefreshCw className="w-4 h-4" />
              重新生成
            </button>
          </div>
        )}
      </div>

      {/* Competitors */}
      <section>
        <h2 className="text-lg font-semibold text-gray-800 mb-2">Competitors</h2>
        <div className="flex flex-wrap gap-2">
          {task.competitors.map((c, i) => {
            const name = typeof c === "string" ? c : c.name;
            const category = typeof c === "string" ? "" : c.category;
            const website = typeof c === "string" ? null : c.website;
            return (
              <span key={i} className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 rounded-full text-sm text-gray-700">
                {name}
                {category && category !== "direct" && (
                  <span className="text-xs text-gray-400">({category})</span>
                )}
                {website && (
                  <a href={website} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline text-xs ml-1">🔗</a>
                )}
              </span>
            );
          })}
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

      {/* Polling indicator & SSE Real-time Updates */}
      {polling && (
        <div className="bg-white border rounded-xl p-6 shadow-sm flex flex-col gap-4">
          <div className="flex items-center gap-3 text-blue-600 font-medium">
            <span className="animate-spin inline-block w-5 h-5 border-2 border-current border-t-transparent rounded-full" />
            分析进行中...
          </div>
          
          {sseEvent && (
            <div className="bg-gray-50 p-4 rounded-lg border text-sm text-gray-700 space-y-2">
              <div className="flex items-center justify-between font-semibold">
                <span className="uppercase text-blue-700">{sseEvent.agent}</span>
                <span>{sseEvent.status}</span>
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-500">
                {sseEvent.duration !== undefined && <div>耗时: {sseEvent.duration}s</div>}
                {sseEvent.tokens !== undefined && <div>Tokens: {sseEvent.tokens}</div>}
                {sseEvent.passed !== undefined && (
                  <div className={sseEvent.passed ? "text-green-600" : "text-red-600"}>
                    质检: {sseEvent.passed ? "通过" : "打回"}
                  </div>
                )}
                {sseEvent.retry_target && <div>打回至: {sseEvent.retry_target} (Retry #{sseEvent.retry_count})</div>}
                {sseEvent.removed_claims !== undefined && <div>过滤无引用结论: {sseEvent.removed_claims}条</div>}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Add Source Modal */}
      {showSourceModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
            <h2 className="text-xl font-bold mb-4">补充资料</h2>
            <form onSubmit={handleAddSource} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">标题</label>
                <input required type="text" className="w-full border rounded-lg p-2" value={newSource.title} onChange={e => setNewSource({...newSource, title: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">URL (可选)</label>
                <input type="url" className="w-full border rounded-lg p-2" value={newSource.url} onChange={e => setNewSource({...newSource, url: e.target.value})} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">资料摘要 / 内容</label>
                <textarea required rows={4} className="w-full border rounded-lg p-2" value={newSource.content_snippet} onChange={e => setNewSource({...newSource, content_snippet: e.target.value})} />
              </div>
              <div className="flex gap-3 justify-end mt-6">
                <button type="button" onClick={() => setShowSourceModal(false)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">取消</button>
                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">提交资料</button>
              </div>
            </form>
          </div>
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
