import { Suspense, lazy, useEffect, useRef, useState, type FormEvent } from "react";
import { useParams, Link } from "react-router-dom";
import {
  taskApi,
  metricsApi,
  analysisApi,
  externalHref,
  formatWebsiteLabel,
  type AnalysisData,
  type CurationSummary,
  type ConstraintSummary,
  type RunHistoryCompareResponse,
  type RunHistorySummary,
  type Task,
  type Metrics,
  type SSEEvent,
} from "../api/client";
import { useToast } from "../components/Toast";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ClipboardList,
  ExternalLink,
  Layers3,
  MessageSquareText,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from "lucide-react";

const LazyDagView = lazy(() => import("../components/DagView"));
const LazyComparisonMatrix = lazy(() => import("../components/ComparisonMatrix"));

const ACTIVE_STATUSES = new Set([
  "collecting",
  "surveying",
  "interviewing",
  "fieldwork",
  "curating",
  "analyzing",
  "writing",
  "screenshotting",
  "filtering",
  "qa",
  "retrying",
]);

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  collecting: "bg-blue-100 text-blue-700",
  surveying: "bg-cyan-100 text-cyan-700",
  interviewing: "bg-teal-100 text-teal-700",
  fieldwork: "bg-emerald-100 text-emerald-700",
  curating: "bg-sky-100 text-sky-700",
  analyzing: "bg-indigo-100 text-indigo-700",
  writing: "bg-purple-100 text-purple-700",
  screenshotting: "bg-fuchsia-100 text-fuchsia-700",
  filtering: "bg-yellow-100 text-yellow-700",
  qa: "bg-orange-100 text-orange-700",
  retrying: "bg-amber-100 text-amber-700",
  awaiting_review: "bg-cyan-100 text-cyan-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "待启动",
  collecting: "采集中",
  surveying: "问卷设计中",
  interviewing: "访谈设计中",
  fieldwork: "调研执行中",
  curating: "证据筛选中",
  analyzing: "分析中",
  writing: "写作中",
  screenshotting: "截图处理中",
  filtering: "过滤中",
  qa: "质检中",
  retrying: "返工中",
  awaiting_review: "等待人工确认",
  completed: "已完成",
  failed: "失败",
};

const CURATION_REASON_LABELS: Record<string, string> = {
  selected: "已纳入分析",
  duplicate_url: "重复 URL",
  duplicate_content: "重复内容",
  low_reliability: "低可信度",
  domain_cap: "单域名来源过多",
  max_source_cap: "超过来源上限",
};

function getCurationReasonLabel(reason: string) {
  return CURATION_REASON_LABELS[reason] ?? reason.replace(/_/g, " ");
}

function hasCurationSummary(summary: CurationSummary | null | undefined) {
  return Boolean(summary && Object.keys(summary).length > 0);
}

function formatReliability(value: number | null | undefined) {
  if (value == null) {
    return "--";
  }
  return `${(value * 100).toFixed(0)}%`;
}

function getStatusLabel(status: string) {
  return STATUS_LABELS[status] ?? status;
}


function SectionLoading({ label }: { label: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-8 text-center text-sm text-gray-500">
      {label}
    </div>
  );
}

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>();
  const { toast } = useToast();
  const [task, setTask] = useState<Task | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [constraints, setConstraints] = useState<ConstraintSummary[]>([]);
  const [runs, setRuns] = useState<RunHistorySummary[]>([]);
  const [runCompare, setRunCompare] = useState<RunHistoryCompareResponse | null>(null);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState("");
  const [sseEvent, setSseEvent] = useState<SSEEvent | null>(null);
  const [showSourceModal, setShowSourceModal] = useState(false);
  const [showRerunModal, setShowRerunModal] = useState(false);
  const [newSource, setNewSource] = useState({ title: "", url: "", content_snippet: "", type: "url" });
  const [reviewInstruction, setReviewInstruction] = useState("");
  const [continuingReview, setContinuingReview] = useState(false);
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const sseErrorCountRef = useRef(0);
  const pollFailCountRef = useRef(0);

  const loadTaskSnapshot = async (taskId: string, mode: "full" | "status" = "full") => {
    const taskPromise = taskApi.get(taskId).then((r) => {
      setTask(r.data);
      setPolling(ACTIVE_STATUSES.has(r.data.status));
      if (ACTIVE_STATUSES.has(r.data.status)) {
        setMetrics(null);
        if (mode === "full") {
          setAnalysis(null);
        }
      }
    });

    if (mode === "status") {
      await taskPromise;
      return;
    }

    await Promise.all([
      taskPromise,
      metricsApi.get(taskId).then((r) => setMetrics(r.data)).catch(() => setMetrics(null)),
      analysisApi.get(taskId).then((r) => setAnalysis(r.data)).catch(() => setAnalysis(null)),
      taskApi.constraints(taskId).then((r) => setConstraints(r.data)).catch(() => setConstraints([])),
      taskApi.runs(taskId).then((r) => setRuns(r.data)).catch(() => setRuns([])),
      taskApi.compareLatestRuns(taskId).then((r) => setRunCompare(r.data)).catch(() => setRunCompare(null)),
    ]);
  };

  useEffect(() => {
    if (!id) return;
    loadTaskSnapshot(id).catch(() => setError("任务未找到"));
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
        sseErrorCountRef.current += 1;
        if (sseErrorCountRef.current >= 6) {
          source.close();
          pollFailCountRef.current = 0;
        }
      };
    };

    setupSSE();
    sseErrorCountRef.current = 0;

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [id, polling]);

  // Fallback Polling (in case SSE fails/drops)
  useEffect(() => {
    if (!id || !polling) return;
    pollFailCountRef.current = 0;
    const interval = setInterval(async () => {
      try {
        const r = await taskApi.getStatus(id);
        pollFailCountRef.current = 0;
        setTask((prev) => (prev ? { ...prev, status: r.data.status } : prev));
        if (["completed", "failed"].includes(r.data.status)) {
          setPolling(false);
          setSseEvent(null);
          if (eventSourceRef.current) {
            eventSourceRef.current.close();
          }
          loadTaskSnapshot(id).catch(() => {
            console.warn("Failed to refresh task snapshot after completion for", id);
          });
        }
      } catch {
        pollFailCountRef.current += 1;
        if (pollFailCountRef.current >= 15) {
          setPolling(false);
          setTask((prev) => (prev ? { ...prev, status: "failed" } : prev));
          if (eventSourceRef.current) {
            eventSourceRef.current.close();
          }
          toast("后端持续无响应，已停止轮询。请检查网络后重试。", "error");
        }
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [id, polling]);

  const handleRun = async () => {
    if (!id) return;
    try {
      setError("");
      await taskApi.run(id);
      setMetrics(null);
      setAnalysis(null);
      setPolling(true);
      setSseEvent(null);
      setTask((prev) => (
        prev
          ? {
              ...prev,
              status: "collecting",
              last_qa_feedback: {},
              last_handoff: {},
              last_curation_summary: {},
            }
          : prev
      ));
    } catch (e: any) {
      setError(e.response?.data?.detail || "启动分析失败");
    }
  };

  const handleRerun = async () => {
    if (!id) return;
    try {
      setError("");
      await taskApi.rerun(id);
      setMetrics(null);
      setAnalysis(null);
      setPolling(true);
      setSseEvent(null);
      setTask((prev) => (
        prev
          ? {
              ...prev,
              status: "collecting",
              last_qa_feedback: {},
              last_handoff: {},
              last_curation_summary: {},
            }
          : prev
      ));
    } catch (e: any) {
      setError(e.response?.data?.detail || "重新生成失败");
    }
  };

  const handleContinueAfterReview = async (e: FormEvent) => {
    e.preventDefault();
    if (!id) return;
    try {
      setContinuingReview(true);
      setError("");
      await taskApi.continueAfterReview(id, reviewInstruction);
      setReviewInstruction("");
      setPolling(true);
      setTask((prev) => (prev ? { ...prev, status: "writing" } : prev));
      toast("已继续执行，系统会从报告撰写节点恢复。", "success");
    } catch (err: any) {
      toast(err.response?.data?.detail || "继续执行失败", "error");
    } finally {
      setContinuingReview(false);
    }
  };

  const handleAddSource = async (e: FormEvent) => {
    e.preventDefault();
    if (!id) return;
    try {
      await taskApi.submitCorrection(id, {
        correction_type: "add_source",
        data: newSource,
      });
      setShowSourceModal(false);
      setNewSource({ title: "", url: "", content_snippet: "", type: "url" });
      loadTaskSnapshot(id).catch(() => {
        console.warn("Failed to refresh after adding source for", id);
      });
      // Suggest rerun
      toast("资料已补充！请点击「保留资料重生成」以纳入新资料并修正报告。", "success");
    } catch (err) {
      toast("补充资料失败", "error");
    }
  };

  if (error) return <div className="p-8 text-red-600">{error}</div>;
  if (!task) return <div className="p-8 text-gray-500">加载中...</div>;

  const statusClass = STATUS_COLORS[task.status] || "bg-gray-100 text-gray-700";
  const qaPassed = task.last_qa_feedback?.passed === true;
  const qaIssues = Array.isArray(task.last_qa_feedback?.issues)
    ? (task.last_qa_feedback.issues as Array<Record<string, unknown>>)
    : [];
  const handoff = typeof task.last_handoff === "object" && task.last_handoff
    ? (task.last_handoff as Record<string, unknown>)
    : {};
  const curationSummary = task.last_curation_summary ?? {};
  const curationReady = hasCurationSummary(curationSummary);
  const removedReasons = Object.entries(curationSummary.removed_reasons ?? {}).sort((a, b) => b[1] - a[1]);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      <Link to="/tasks" className="text-sm text-gray-400 hover:text-gray-600 inline-flex items-center gap-1">
        <ArrowLeft className="w-3.5 h-3.5" /> 返回工作台
      </Link>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{task.target_product}</h1>
          <p className="text-sm text-gray-500 mt-1">
            {task.industry || "未填写行业"} &middot; {task.competitors.length} 个竞品
          </p>
          {task.target_website ? (
            <a
              href={externalHref(task.target_website)}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-flex items-center gap-2 rounded-full border border-cyan-100 bg-cyan-50 px-3 py-1.5 text-sm font-medium text-cyan-700 transition-colors hover:border-cyan-200 hover:bg-cyan-100"
              title={task.target_website}
            >
              <ExternalLink className="h-4 w-4" />
              目标官网：{formatWebsiteLabel(task.target_website)}
            </a>
          ) : null}
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusClass}`}>
          {getStatusLabel(task.status)}
        </span>
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        {["pending", "failed"].includes(task.status) && (
          <button
            onClick={handleRun}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition whitespace-nowrap"
          >
            {task.status === "failed" ? "重新开始" : "启动分析"}
          </button>
        )}
        {task.status === "completed" && (
          <div className="flex flex-wrap gap-3">
            <Link
              to={`/tasks/${id}/report`}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition whitespace-nowrap"
            >
              查看报告
            </Link>
            <Link
              to={`/tasks/${id}/traces`}
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2 transition whitespace-nowrap"
            >
              <Activity className="w-4 h-4" />
              执行追踪
            </Link>
            <Link
              to={`/tasks/${id}/survey`}
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2 transition whitespace-nowrap"
            >
              <ClipboardList className="w-4 h-4" />
              问卷
            </Link>
            <Link
              to={`/tasks/${id}/interview`}
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2 transition whitespace-nowrap"
            >
              <MessageSquareText className="w-4 h-4" />
              访谈提纲
            </Link>
            <button
              onClick={() => setShowSourceModal(true)}
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2 transition whitespace-nowrap"
            >
              <Plus className="w-4 h-4" />
              补充资料
            </button>
            <button
              onClick={() => setShowRerunModal(true)}
              className="px-4 py-2 bg-white border border-blue-300 text-blue-700 rounded-lg hover:bg-blue-50 flex items-center gap-2 transition whitespace-nowrap"
              title="选择重跑模式：全量重跑 或 保留资料重生成"
            >
              <RefreshCw className="w-4 h-4" />
              重跑
            </button>
          </div>
        )}
      </div>

      {/* Rerun Mode Modal */}
      {showRerunModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowRerunModal(false)}>
          <div
            role="dialog" aria-modal="true" aria-label="选择重跑模式"
            className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-gray-900 mb-4">选择重跑模式</h2>
            <div className="space-y-3">
              <button
                onClick={() => { setShowRerunModal(false); handleRun(); }}
                className="w-full rounded-xl border border-gray-200 bg-gray-50 px-5 py-4 text-left hover:border-blue-200 hover:bg-blue-50 transition"
              >
                <div className="font-semibold text-gray-900">全量重跑</div>
                <div className="mt-1 text-sm text-gray-500">
                  清空当前结果与资料，从头重新运行完整流水线
                </div>
              </button>
              <button
                onClick={() => { setShowRerunModal(false); handleRerun(); }}
                className="w-full rounded-xl border border-gray-200 bg-gray-50 px-5 py-4 text-left hover:border-blue-200 hover:bg-blue-50 transition"
              >
                <div className="font-semibold text-gray-900">保留资料重生成</div>
                <div className="mt-1 text-sm text-gray-500">
                  保留已采集的来源和约束，只重新生成报告、问卷等产物
                </div>
              </button>
            </div>
            <button
              onClick={() => setShowRerunModal(false)}
              className="mt-4 w-full py-2 text-sm text-gray-500 hover:text-gray-700 transition"
            >
              取消
            </button>
          </div>
        </div>
      )}

      {task.status === "awaiting_review" && (
        <section className="rounded-2xl border border-cyan-200 bg-cyan-50 p-5">
          <div className="flex items-center gap-2 text-cyan-950">
            <ShieldCheck className="h-4 w-4 text-cyan-700" />
            <h2 className="text-lg font-semibold">人工确认点</h2>
          </div>
          <p className="mt-2 text-sm leading-6 text-cyan-900/80">
            结构化分析已经完成，报告撰写会在你确认后继续。这里填写的内容会作为 writer 约束进入 checkpoint 后续执行。
          </p>
          <form onSubmit={handleContinueAfterReview} className="mt-4 space-y-3">
            <textarea
              rows={3}
              value={reviewInstruction}
              onChange={(event) => setReviewInstruction(event.target.value)}
              placeholder="例如：报告优先突出企业治理能力，不要把价格作为唯一建议依据。"
              className="w-full rounded-xl border border-cyan-200 bg-white px-4 py-3 text-sm leading-6 text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-cyan-400"
            />
            <button
              type="submit"
              disabled={continuingReview}
              className="inline-flex items-center gap-2 rounded-xl bg-cyan-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-cyan-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 ${continuingReview ? "animate-spin" : ""}`} />
              {continuingReview ? "继续中..." : "确认并继续生成报告"}
            </button>
          </form>
        </section>
      )}

      {/* Competitors */}
      <section>
        <h2 className="text-lg font-semibold text-gray-800 mb-2">竞品范围</h2>
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
                  <a href={externalHref(website)} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline text-xs ml-1">🔗</a>
                )}
              </span>
            );
          })}
          {task.competitors.length === 0 && (
            <span className="text-sm text-gray-400">暂未指定竞品</span>
          )}
        </div>
      </section>

      {(task.focus_areas?.length > 0 || task.our_product_notes) && (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-gray-200 bg-white p-5">
            <div className="flex items-center gap-2 text-gray-900">
              <Layers3 className="h-4 w-4 text-blue-600" />
              <h2 className="text-lg font-semibold">分析边界</h2>
            </div>
            {task.focus_areas?.length > 0 ? (
              <div className="mt-4 flex flex-wrap gap-2">
                {task.focus_areas.map((area) => (
                  <span key={area} className="rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-700">
                    {area}
                  </span>
                ))}
              </div>
            ) : (
              <p className="mt-4 text-sm text-gray-500">当前没有显式指定重点分析维度。</p>
            )}
          </div>

          <div className="rounded-2xl border border-gray-200 bg-white p-5">
            <div className="flex items-center gap-2 text-gray-900">
              <Sparkles className="h-4 w-4 text-blue-600" />
              <h2 className="text-lg font-semibold">研究背景 / 分析说明</h2>
            </div>
            <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-gray-600">
              {task.our_product_notes?.trim() || "当前没有补充研究背景或分析说明。"}
            </p>
          </div>
        </section>
      )}

      {/* Metrics */}
      {metrics && (
        <section>
          <h2 className="text-lg font-semibold text-gray-800 mb-3">质量指标</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <MetricCard label="分析证据" value={metrics.source_count} />
            <MetricCard label="结论数" value={metrics.claim_count} />
            <MetricCard label="证据覆盖率" value={`${(metrics.evidence_coverage_rate * 100).toFixed(1)}%`} />
            <MetricCard label="质量分" value={`${(metrics.quality_score * 100).toFixed(1)}%`} />
            <MetricCard label="人工修正" value={metrics.manual_correction_count} />
          </div>
          <p className="mt-3 text-sm text-gray-500">
            质量分综合证据覆盖、引用密度、结构化完整度和来源质量；“分析证据”指最终纳入分析链路的来源，不包含被筛除的候选资料。
          </p>
        </section>
      )}

      {!polling && (
        <section className="rounded-2xl border border-gray-200 bg-white p-5">
          <div className="flex items-center gap-2 text-gray-900">
            <Sparkles className="h-4 w-4 text-blue-600" />
            <h2 className="text-lg font-semibold">最近一次证据筛选</h2>
          </div>
          {curationReady ? (
            <div className="mt-4 space-y-4">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                <MetricCard label="候选来源" value={curationSummary.input_count ?? 0} />
                <MetricCard label="纳入分析" value={curationSummary.kept_count ?? 0} />
                <MetricCard label="已筛除" value={curationSummary.removed_count ?? 0} />
                <MetricCard label="一手证据" value={curationSummary.first_party_count ?? 0} />
                <MetricCard label="平均可信度" value={formatReliability(curationSummary.avg_reliability)} />
              </div>
              {removedReasons.length > 0 ? (
                <div>
                  <div className="text-sm font-medium text-gray-700">主要筛除原因</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {removedReasons.map(([reason, count]) => (
                      <span
                        key={reason}
                        className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700"
                      >
                        {getCurationReasonLabel(reason)} {count} 条
                      </span>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-gray-500">
                  本次没有记录明确的筛除原因，说明大多数来源都被直接纳入分析。
                </p>
              )}
            </div>
          ) : (
            <p className="mt-4 text-sm text-gray-500">任务尚未完成证据筛选，运行完成后这里会展示筛选结果。</p>
          )}
        </section>
      )}

      {!polling && analysis && (
        <section className="space-y-3">
          <div className="flex items-center gap-2 text-gray-900">
            <Sparkles className="h-4 w-4 text-blue-600" />
            <h2 className="text-lg font-semibold">结构化分析产物</h2>
          </div>
          <Suspense fallback={<SectionLoading label="正在加载结构化分析视图..." />}>
            <LazyComparisonMatrix analysis={analysis} />
          </Suspense>
        </section>
      )}

      {!polling && runCompare?.current && (
        <section className="rounded-2xl border border-gray-200 bg-white p-5">
          <div className="flex items-center gap-2 text-gray-900">
            <TrendingUp className="h-4 w-4 text-blue-600" />
            <h2 className="text-lg font-semibold">最近两次运行对比</h2>
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-6">
            <HistoryMetric
              label="分析证据"
              current={runCompare.current.source_count}
              delta={runCompare.delta?.source_count_delta}
            />
            <HistoryMetric
              label="结论数"
              current={runCompare.current.claim_count}
              delta={runCompare.delta?.claim_count_delta}
            />
            <HistoryMetric
              label="证据覆盖率"
              current={`${(runCompare.current.evidence_coverage_rate * 100).toFixed(1)}%`}
              delta={runCompare.delta ? `${formatSignedPercent(runCompare.delta.evidence_coverage_delta)}` : undefined}
            />
            <HistoryMetric
              label="质量分"
              current={`${(runCompare.current.quality_score * 100).toFixed(1)}%`}
              delta={runCompare.delta ? `${formatSignedPercent(runCompare.delta.quality_score_delta)}` : undefined}
            />
            <HistoryMetric
              label="重试次数"
              current={runCompare.current.retry_count}
              delta={runCompare.delta?.retry_count_delta}
              invertDelta
            />
            <HistoryMetric
              label="人工修正"
              current={runCompare.current.manual_correction_count}
              delta={runCompare.delta?.manual_correction_delta}
              invertDelta
            />
          </div>
          {runCompare.previous ? (
            <div className="mt-4 space-y-1 text-sm text-gray-500">
              <p>当前对比的是第 {runCompare.current.run_index} 次运行和第 {runCompare.previous.run_index} 次运行。</p>
              <p>这里的“分析证据”指最终被纳入分析的来源，不含被筛除的候选来源。</p>
            </div>
          ) : (
            <div className="mt-4 space-y-1 text-sm text-gray-500">
              <p>当前只有一次运行记录，后续重跑后这里会展示改进幅度。</p>
              <p>这里的“分析证据”指最终被纳入分析的来源，不含被筛除的候选来源。</p>
            </div>
          )}
        </section>
      )}

      {!polling && (
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-gray-200 bg-white p-5">
            <div className="flex items-center gap-2 text-gray-900">
              {qaPassed ? (
                <ShieldCheck className="h-4 w-4 text-green-600" />
              ) : (
                <AlertTriangle className="h-4 w-4 text-amber-600" />
              )}
              <h2 className="text-lg font-semibold">最近一次质检</h2>
            </div>
            {!task.last_qa_feedback || Object.keys(task.last_qa_feedback).length === 0 ? (
              <p className="mt-4 text-sm text-gray-500">任务尚未产出 QA 结果。</p>
            ) : (
              <div className="mt-4 space-y-3">
                <div className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ${
                  qaPassed ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
                }`}>
                  {qaPassed ? "QA 通过" : "QA 打回 / 待处理"}
                </div>
                {qaIssues.length > 0 ? (
                  <div className="space-y-2">
                    {qaIssues.slice(0, 4).map((issue, index) => (
                      <div key={`${issue.field_path ?? "issue"}-${index}`} className="rounded-xl bg-gray-50 p-3 text-sm text-gray-700">
                        <div className="font-medium text-gray-900">
                          {String(issue.issue_type ?? "issue")}
                          {issue.field_path ? ` · ${String(issue.field_path)}` : ""}
                        </div>
                        <div className="mt-1 text-gray-600">{String(issue.description ?? "")}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">本次 QA 没有记录结构化问题列表。</p>
                )}
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-gray-200 bg-white p-5">
            <div className="flex items-center gap-2 text-gray-900">
              <RefreshCw className="h-4 w-4 text-blue-600" />
              <h2 className="text-lg font-semibold">返工指令与约束</h2>
            </div>
            {Object.keys(handoff).length > 0 ? (
              <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900">
                <div>目标 Agent：{String(handoff.target_agent ?? "-")}</div>
                <div className="mt-1">问题类型：{String(handoff.issue_type ?? "-")}</div>
                {Array.isArray(handoff.failed_fields) && (handoff.failed_fields as unknown[]).length > 0 ? (
                  <div className="mt-1">
                    失败字段：{(handoff.failed_fields as unknown[]).map(String).join("、")}
                  </div>
                ) : null}
                {handoff.evidence_requirements ? (
                  <div className="mt-1">证据要求：{String(handoff.evidence_requirements)}</div>
                ) : null}
              </div>
            ) : (
              <p className="mt-4 text-sm text-gray-500">当前没有待执行的结构化返工指令。</p>
            )}

            <div className="mt-4 space-y-2">
              {constraints.length > 0 ? (
                constraints.slice(0, 6).map((constraint) => (
                  <div key={constraint.id} className="rounded-xl bg-gray-50 p-3 text-sm text-gray-700">
                    <div className="font-medium text-gray-900">
                      {constraint.applied_to || "unknown"} · {constraint.constraint_type}
                    </div>
                    <div className="mt-1">{constraint.constraint_value}</div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500">暂时还没有积累下来的约束规则。</p>
              )}
            </div>
          </div>
        </section>
      )}

      {!polling && runs.length > 0 && (
        <section className="rounded-2xl border border-gray-200 bg-white p-5">
          <div className="flex items-center gap-2 text-gray-900">
            <Activity className="h-4 w-4 text-blue-600" />
            <h2 className="text-lg font-semibold">运行历史</h2>
          </div>
          <div className="mt-4 space-y-3">
            {runs.map((run) => (
              <div key={run.id} className="rounded-xl bg-gray-50 p-4">
                <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-white px-3 py-1 text-sm font-medium text-gray-700">
                      第 {run.run_index} 次运行
                    </span>
                    <span className={`rounded-full px-3 py-1 text-xs font-medium ${STATUS_COLORS[run.status] ?? "bg-gray-100 text-gray-700"}`}>
                      {getStatusLabel(run.status)}
                    </span>
                    <span className="text-sm text-gray-500">
                      {new Date(run.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="text-sm text-gray-500">
                    证据 {run.source_count} · 结论 {run.claim_count} · 覆盖率 {(run.evidence_coverage_rate * 100).toFixed(1)}% · 质量分 {(run.quality_score * 100).toFixed(1)}%
                  </div>
                </div>
                {hasCurationSummary(run.curation_summary) ? (
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    <span className="rounded-full bg-white px-3 py-1 text-gray-600">
                      筛选 {run.curation_summary.kept_count ?? run.source_count}/{run.curation_summary.input_count ?? run.source_count}
                    </span>
                    {(run.curation_summary.removed_count ?? 0) > 0 ? (
                      <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-700">
                        筛除 {run.curation_summary.removed_count} 条
                      </span>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ))}
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

          {/* DAG Progress */}
          {id && (
            <div className="rounded-lg border bg-gray-50 p-2">
              <Suspense fallback={<SectionLoading label="正在加载执行链路图..." />}>
                <LazyDagView taskId={id} height="220px" />
              </Suspense>
            </div>
          )}
          
          {sseEvent && (
            <div className="bg-gray-50 p-4 rounded-lg border text-sm text-gray-700 space-y-2">
              <div className="flex items-center justify-between font-semibold">
                <span className="uppercase text-blue-700">{sseEvent.agent}</span>
                <span>{sseEvent.status}</span>
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-500">
                {sseEvent.duration !== undefined && <div>耗时: {sseEvent.duration}s</div>}
                {sseEvent.tokens !== undefined && <div>Tokens：{sseEvent.tokens}</div>}
                {sseEvent.passed !== undefined && (
                  <div className={sseEvent.passed ? "text-green-600" : "text-red-600"}>
                    质检: {sseEvent.passed ? "通过" : "打回"}
                  </div>
                )}
                {sseEvent.retry_target && <div>打回至: {sseEvent.retry_target}（第 {sseEvent.retry_count} 次重试）</div>}
                {sseEvent.removed_claims !== undefined && <div>过滤无引用结论: {sseEvent.removed_claims}条</div>}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Add Source Modal */}
      {showSourceModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div role="dialog" aria-modal="true" aria-label="补充资料" className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
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

function formatSignedPercent(value: number) {
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${(value * 100).toFixed(1)}%`;
}

function HistoryMetric({
  label,
  current,
  delta,
  invertDelta = false,
}: {
  label: string;
  current: string | number;
  delta?: string | number;
  invertDelta?: boolean;
}) {
  const numericDelta = typeof delta === "number" ? delta : undefined;
  const resolvedDelta = numericDelta ?? 0;
  const deltaClass = delta === undefined
    ? "text-gray-400"
    : typeof delta === "string"
      ? "text-blue-600"
      : resolvedDelta === 0
        ? "text-gray-500"
        : ((resolvedDelta > 0) !== invertDelta ? "text-green-600" : "text-red-600");
  const deltaText = delta === undefined
    ? "—"
    : typeof delta === "string"
      ? delta
      : `${resolvedDelta > 0 ? "+" : ""}${resolvedDelta}`;

  return (
    <div className="rounded-xl bg-gray-50 p-4">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-gray-900">{current}</div>
      <div className={`mt-2 text-sm font-medium ${deltaClass}`}>较上次 {deltaText}</div>
    </div>
  );
}
