import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  ExternalLink,
  Clock,
  Activity,
  Play,
  Loader2,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ArrowRight,
  RotateCcw,
  X,
  Quote,
  Shield,
} from "lucide-react";
import {
  taskApi,
  reportApi,
  sourceApi,
  traceApi,
  type Task,
  type Report,
  type Source,
  type Trace,
} from "../api/client";

const statusLabel: Record<string, { text: string; cls: string }> = {
  pending: { text: "待执行", cls: "bg-gray-100 text-gray-700" },
  running: { text: "执行中", cls: "bg-blue-100 text-blue-700" },
  completed: { text: "已完成", cls: "bg-green-100 text-green-700" },
  failed: { text: "失败", cls: "bg-red-100 text-red-700" },
};

function formatTime(iso: string) {
  return new Date(iso).toLocaleString("zh-CN");
}

type TabKey = "report" | "sources" | "traces";

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>();
  const [task, setTask] = useState<Task | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [traces, setTraces] = useState<Trace[]>([]);
  const [activeTab, setActiveTab] = useState<TabKey>("report");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const loadTaskData = async () => {
    if (!id) return;
    setLoading(true);
    const [t, r, s, tr] = await Promise.all([
      taskApi.get(id).catch(() => null),
      reportApi.get(id).catch(() => null),
      sourceApi.list(id).catch(() => []),
      traceApi.list(id).catch(() => []),
    ]);
    setTask((t as { data: Task })?.data ?? null);
    setReport((r as { data: Report })?.data ?? null);
    setSources(((s as { data: Source[] })?.data ?? []) as Source[]);
    setTraces(((tr as { data: Trace[] })?.data ?? []) as Trace[]);
    setLoading(false);
  };

  useEffect(() => {
    loadTaskData();
  }, [id]);

  const handleRun = async () => {
    if (!id || running) return;
    setRunning(true);
    try {
      const resp = await taskApi.run(id);
      setTask(resp.data);
      await loadTaskData();
      setActiveTab("report");
    } catch {
      alert("运行失败，请稍后重试");
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-gray-400">
        加载中…
      </div>
    );
  }

  if (!task) {
    return (
      <div className="text-center py-20">
        <h2 className="text-lg font-medium text-gray-600">任务不存在</h2>
        <Link
          to="/tasks"
          className="mt-4 inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
        >
          <ArrowLeft className="w-4 h-4" /> 返回任务列表
        </Link>
      </div>
    );
  }

  const st = statusLabel[task.status] ?? {
    text: task.status,
    cls: "bg-gray-100 text-gray-700",
  };

  const tabs: { key: TabKey; label: string; icon: typeof FileText }[] = [
    { key: "report", label: "报告", icon: FileText },
    { key: "sources", label: "数据来源", icon: ExternalLink },
    { key: "traces", label: "执行追踪", icon: Activity },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Link
          to="/tasks"
          className="mt-1 p-1 text-gray-400 hover:text-gray-600 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">
              {task.target_product}
            </h1>
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${st.cls}`}
            >
              {st.text}
            </span>
          </div>
          <div className="mt-1 flex items-center gap-4 text-sm text-gray-500">
            {task.industry && <span>行业: {task.industry}</span>}
            {task.competitors.length > 0 && (
              <span>竞品: {task.competitors.join("、")}</span>
            )}
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              {formatTime(task.created_at)}
            </span>
          </div>
        </div>
        {(task.status === "pending" || task.status === "failed" || task.status === "running") && (
          <button
            type="button"
            onClick={handleRun}
            disabled={running || task.status === "running"}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {running || task.status === "running" ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                执行中…
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                运行分析
              </>
            )}
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-1.5 pb-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === "report" && (
          <ReportTab report={report} taskStatus={task.status} sources={sources} />
        )}
        {activeTab === "sources" && <SourcesTab sources={sources} />}
        {activeTab === "traces" && <TracesTab traces={traces} />}
      </div>
    </div>
  );
}

// --- Claim / Evidence type for report sections ---
interface ClaimData {
  id: string;
  content: string;
  evidence_ids: string[];
  confidence: number;
  category: string;
}

interface SectionData {
  title: string;
  content: string;
  claims: ClaimData[];
}

function ReportTab({
  report,
  taskStatus,
  sources,
}: {
  report: Report | null;
  taskStatus: string;
  sources: Source[];
}) {
  // Track which source ID is currently highlighted
  const [highlightSourceId, setHighlightSourceId] = useState<string | null>(null);

  if (!report) {
    return (
      <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-100 text-center">
        <FileText className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <p className="text-gray-500">
          {taskStatus === "pending"
            ? "任务待执行，暂无报告"
            : "报告生成中，请稍后查看"}
        </p>
      </div>
    );
  }

  const content = report.content as Record<string, unknown>;
  const sections = (content.sections ?? []) as SectionData[];
  const executiveSummary = (content.executive_summary ?? "") as string;

  // Build source lookup map
  const sourceMap = new Map<string, Source>();
  sources.forEach((s) => sourceMap.set(s.id, s));

  // Get highlighted source info for the banner
  const highlightedSource = highlightSourceId ? sourceMap.get(highlightSourceId) : null;

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 space-y-6 relative">
      <div>
        <h2 className="text-xl font-bold text-gray-900">{report.title}</h2>
        <p className="text-xs text-gray-400 mt-1">
          生成于 {formatTime(report.created_at)}
        </p>
      </div>

      {/* Source highlight banner */}
      {highlightedSource && (
        <div className="sticky top-0 z-10 bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <ExternalLink className="w-4 h-4 text-blue-600 flex-shrink-0" />
            <div className="min-w-0">
              <p className="text-xs font-semibold text-blue-800 truncate">
                正在高亮来源：{highlightedSource.title}
              </p>
              <p className="text-xs text-blue-600 truncate">
                {highlightedSource.content_snippet?.slice(0, 80) || highlightedSource.url || ""}
              </p>
            </div>
          </div>
          <button
            onClick={() => setHighlightSourceId(null)}
            className="p-1 text-blue-400 hover:text-blue-700 flex-shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {executiveSummary && (
        <div className="bg-blue-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-blue-800 mb-1">
            执行摘要
          </h3>
          <p className="text-sm text-blue-900 whitespace-pre-wrap">
            {executiveSummary}
          </p>
        </div>
      )}

      {sections.map((sec, i) => (
        <div key={i} className="space-y-3">
          <h3 className="text-base font-semibold text-gray-900">
            {sec.title}
          </h3>
          <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
            {sec.content}
          </p>

          {/* Claims with evidence references */}
          {sec.claims && sec.claims.length > 0 && (
            <div className="mt-2 space-y-2">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide flex items-center gap-1">
                <Shield className="w-3 h-3" /> 关键结论与来源
              </p>
              {sec.claims.map((claim, ci) => (
                <ClaimCard
                  key={claim.id || ci}
                  claim={claim}
                  sourceMap={sourceMap}
                  highlightSourceId={highlightSourceId}
                  onSourceClick={(sourceId) =>
                    setHighlightSourceId(
                      highlightSourceId === sourceId ? null : sourceId
                    )
                  }
                />
              ))}
            </div>
          )}
        </div>
      ))}

      {sections.length === 0 && !executiveSummary && (
        <p className="text-sm text-gray-500">报告内容为空</p>
      )}
    </div>
  );
}

function ClaimCard({
  claim,
  sourceMap,
  highlightSourceId,
  onSourceClick,
}: {
  claim: ClaimData;
  sourceMap: Map<string, Source>;
  highlightSourceId: string | null;
  onSourceClick: (sourceId: string) => void;
}) {
  // Check if this claim is highlighted (i.e. references the highlighted source)
  const isHighlighted =
    highlightSourceId != null &&
    claim.evidence_ids?.includes(highlightSourceId);

  return (
    <div
      className={`rounded-lg p-3 border transition-all ${
        isHighlighted
          ? "bg-yellow-50 border-yellow-300 border-l-4 border-l-yellow-500"
          : "bg-gray-50 border-gray-100"
      }`}
    >
      <div className="flex items-start gap-2">
        <Quote className="w-3.5 h-3.5 text-gray-400 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p
            className={`text-sm ${
              isHighlighted
                ? "text-gray-900 underline decoration-yellow-400 decoration-2 underline-offset-2"
                : "text-gray-800"
            }`}
          >
            {claim.content}
          </p>
          <div className="mt-1.5 flex items-center gap-2 flex-wrap">
            {/* Evidence source buttons */}
            {claim.evidence_ids &&
              claim.evidence_ids.map((eid, idx) => {
                const source = sourceMap.get(eid);
                const isActive = highlightSourceId === eid;
                return (
                  <button
                    key={eid}
                    onClick={() => onSourceClick(eid)}
                    className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium transition-colors ${
                      isActive
                        ? "bg-yellow-200 text-yellow-900 ring-1 ring-yellow-400"
                        : source
                          ? "bg-blue-50 text-blue-700 hover:bg-blue-100 cursor-pointer"
                          : "bg-gray-100 text-gray-400 cursor-default"
                    }`}
                    title={source ? source.title : "来源未找到"}
                  >
                    <ExternalLink className="w-2.5 h-2.5" />
                    {source ? source.title.slice(0, 12) : `来源${idx + 1}`}
                  </button>
                );
              })}
          </div>
        </div>
      </div>
    </div>
  );
}

function SourcesTab({ sources }: { sources: Source[] }) {
  if (sources.length === 0) {
    return (
      <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-100 text-center">
        <ExternalLink className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <p className="text-gray-500">暂无数据来源</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {sources.map((s) => (
        <div
          key={s.id}
          className="bg-white rounded-xl p-4 shadow-sm border border-gray-100"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-semibold text-gray-900 truncate">
                {s.title}
              </h4>
              <p className="mt-1 text-xs text-gray-500 line-clamp-2">
                {s.content_snippet}
              </p>
            </div>
            <span className="ml-3 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
              {s.type}
            </span>
          </div>
          {s.url && (
            <a
              href={s.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
            >
              <ExternalLink className="w-3 h-3" /> {s.url}
            </a>
          )}
          <p className="mt-1 text-xs text-gray-400">
            采集于 {formatTime(s.fetched_at)}
          </p>
        </div>
      ))}
    </div>
  );
}

function TracesTab({ traces }: { traces: Trace[] }) {
  if (traces.length === 0) {
    return (
      <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-100 text-center">
        <Activity className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <p className="text-gray-500">暂无执行追踪</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* DAG Flow Visualization */}
      <DAGFlow traces={traces} />

      {/* Timeline */}
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
          <Clock className="w-4 h-4" />
          执行时间线
        </h3>
        <ExecutionTimeline traces={traces} />
      </div>
    </div>
  );
}

// --- DAG Flow Visualization ---

const DAG_NODES = ["collector", "analyst", "writer", "qa"] as const;
const DAG_LABELS: Record<string, string> = {
  collector: "采集",
  analyst: "分析",
  writer: "撰写",
  qa: "质检",
};

function DAGFlow({ traces }: { traces: Trace[] }) {
  // Build execution status for each node
  const nodeStatus = new Map<string, { status: string; count: number }>();
  traces.forEach((t) => {
    const existing = nodeStatus.get(t.agent_name);
    if (existing) {
      existing.count += 1;
      // Prefer completed > failed > running
      if (t.status === "completed") existing.status = "completed";
    } else {
      nodeStatus.set(t.agent_name, { status: t.status, count: 1 });
    }
  });

  // Detect if there was a retry
  const hasRetry = traces.filter((t) => t.agent_name === "qa").length > 1;

  return (
    <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
      <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-1.5">
        <Activity className="w-4 h-4" />
        DAG 执行流程
      </h3>

      <div className="flex items-center justify-center gap-1 overflow-x-auto py-2">
        {DAG_NODES.map((node, idx) => {
          const info = nodeStatus.get(node);
          const status = info?.status ?? "pending";
          const count = info?.count ?? 0;

          return (
            <div key={node} className="flex items-center">
              {/* Node */}
              <div className="flex flex-col items-center">
                <div
                  className={`w-14 h-14 rounded-xl flex items-center justify-center border-2 transition-all ${
                    status === "completed"
                      ? "border-green-300 bg-green-50"
                      : status === "failed"
                        ? "border-red-300 bg-red-50"
                        : "border-gray-200 bg-gray-50"
                  }`}
                >
                  {status === "completed" ? (
                    <CheckCircle2 className="w-6 h-6 text-green-600" />
                  ) : status === "failed" ? (
                    <XCircle className="w-6 h-6 text-red-500" />
                  ) : (
                    <AlertCircle className="w-6 h-6 text-gray-300" />
                  )}
                </div>
                <span className="mt-1.5 text-xs font-medium text-gray-700">
                  {DAG_LABELS[node]}
                </span>
                {count > 1 && (
                  <span className="text-[10px] text-orange-600 font-medium flex items-center gap-0.5">
                    <RotateCcw className="w-2.5 h-2.5" />
                    ×{count}
                  </span>
                )}
              </div>

              {/* Arrow */}
              {idx < DAG_NODES.length - 1 && (
                <div className="mx-2 flex items-center">
                  <ArrowRight className="w-4 h-4 text-gray-300" />
                </div>
              )}
            </div>
          );
        })}

        {/* End node */}
        <div className="flex items-center">
          <div className="mx-2">
            <ArrowRight className="w-4 h-4 text-gray-300" />
          </div>
          <div className="flex flex-col items-center">
            <div className="w-14 h-14 rounded-xl flex items-center justify-center border-2 border-gray-200 bg-gray-50">
              <span className="text-xs font-bold text-gray-500">END</span>
            </div>
            <span className="mt-1.5 text-xs font-medium text-gray-500">
              完成
            </span>
          </div>
        </div>
      </div>

      {/* Retry indicator */}
      {hasRetry && (
        <div className="mt-3 text-center">
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-orange-50 text-orange-700">
            <RotateCcw className="w-3 h-3" />
            QA 打回重试已触发
          </span>
        </div>
      )}
    </div>
  );
}

// --- Execution Timeline ---

interface TraceEvent {
  agent_name: string;
  event_type: string;
  input_summary?: string;
  output_summary?: string;
  error_message?: string;
  token_count?: number;
}

function ExecutionTimeline({ traces }: { traces: Trace[] }) {
  // Group traces into rounds
  const rounds: Trace[][] = [];
  let currentRound: Trace[] = [];
  let qaCount = 0;

  traces.forEach((t) => {
    currentRound.push(t);
    if (t.agent_name === "qa") {
      qaCount++;
      if (qaCount < traces.filter((tr) => tr.agent_name === "qa").length) {
        rounds.push(currentRound);
        currentRound = [];
      }
    }
  });
  if (currentRound.length > 0) {
    rounds.push(currentRound);
  }

  // If only one round, show flat
  if (rounds.length <= 1) {
    return (
      <div className="space-y-2">
        {traces.map((t) => (
          <TimelineEntry key={t.id} trace={t} />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {rounds.map((round, ri) => (
        <div key={ri}>
          <div className="flex items-center gap-2 mb-2">
            <div className="h-px flex-1 bg-gray-200" />
            <span className="text-xs font-medium text-gray-500 px-2">
              {ri === rounds.length - 1 ? "最终轮" : `第 ${ri + 1} 轮`}
              {ri < rounds.length - 1 && (
                <span className="ml-1 text-orange-500">(QA 打回)</span>
              )}
            </span>
            <div className="h-px flex-1 bg-gray-200" />
          </div>
          <div className="space-y-2">
            {round.map((t) => (
              <TimelineEntry key={t.id} trace={t} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function TimelineEntry({ trace }: { trace: Trace }) {
  const [expanded, setExpanded] = useState(false);

  const statusIcon =
    trace.status === "completed" ? (
      <CheckCircle2 className="w-4 h-4 text-green-500" />
    ) : trace.status === "failed" ? (
      <XCircle className="w-4 h-4 text-red-500" />
    ) : (
      <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
    );

  const agentLabel = DAG_LABELS[trace.agent_name] || trace.agent_name;
  const events = (trace.events ?? []) as TraceEvent[];
  const maxDuration = 30; // for progress bar scale
  const durationPct = trace.total_duration
    ? Math.min((trace.total_duration / maxDuration) * 100, 100)
    : 0;

  return (
    <div className="bg-white rounded-lg border border-gray-100 shadow-sm overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-50 transition-colors text-left"
      >
        {/* Timeline dot */}
        {statusIcon}

        {/* Agent name */}
        <span className="text-sm font-semibold text-gray-900 w-16">
          {agentLabel}
        </span>

        {/* Duration bar */}
        <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              trace.status === "completed"
                ? "bg-green-400"
                : trace.status === "failed"
                  ? "bg-red-400"
                  : "bg-blue-400"
            }`}
            style={{ width: `${durationPct}%` }}
          />
        </div>

        {/* Stats */}
        <div className="flex items-center gap-3 text-xs text-gray-500 whitespace-nowrap">
          {trace.total_duration != null && (
            <span>{trace.total_duration.toFixed(1)}s</span>
          )}
          {trace.total_tokens != null && (
            <span>{trace.total_tokens} tok</span>
          )}
        </div>

        {/* Expand icon */}
        {events.length > 0 && (
          expanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          )
        )}
      </button>

      {/* Expanded events */}
      {expanded && events.length > 0 && (
        <div className="border-t border-gray-100 px-4 py-3 bg-gray-50 space-y-2">
          {events.map((evt, ei) => (
            <div
              key={ei}
              className="flex items-start gap-2 text-xs"
            >
              <span
                className={`inline-flex items-center px-1.5 py-0.5 rounded font-medium ${
                  evt.event_type === "error"
                    ? "bg-red-100 text-red-700"
                    : evt.event_type === "output"
                      ? "bg-green-100 text-green-700"
                      : evt.event_type === "start"
                        ? "bg-blue-100 text-blue-700"
                        : "bg-gray-100 text-gray-600"
                }`}
              >
                {evt.event_type}
              </span>
              <div className="flex-1 min-w-0">
                {evt.input_summary && (
                  <p className="text-gray-600 truncate">
                    <span className="text-gray-400">输入:</span> {evt.input_summary}
                  </p>
                )}
                {evt.output_summary && (
                  <p className="text-gray-600 line-clamp-2">
                    <span className="text-gray-400">输出:</span> {evt.output_summary}
                  </p>
                )}
                {evt.error_message && (
                  <p className="text-red-600">
                    <span className="text-red-400">错误:</span> {evt.error_message}
                  </p>
                )}
                {evt.token_count != null && evt.token_count > 0 && (
                  <span className="text-gray-400">({evt.token_count} tokens)</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
