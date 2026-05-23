import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  ExternalLink,
  Clock,
  Cpu,
  Activity,
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

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([
      taskApi.get(id).catch(() => null),
      reportApi.get(id).catch(() => null),
      sourceApi.list(id).catch(() => []),
      traceApi.list(id).catch(() => []),
    ])
      .then(([t, r, s, tr]) => {
        setTask((t as { data: Task })?.data ?? null);
        setReport((r as { data: Report })?.data ?? null);
        setSources(((s as { data: Source[] })?.data ?? []) as Source[]);
        setTraces(((tr as { data: Trace[] })?.data ?? []) as Trace[]);
      })
      .finally(() => setLoading(false));
  }, [id]);

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
          <ReportTab report={report} taskStatus={task.status} />
        )}
        {activeTab === "sources" && <SourcesTab sources={sources} />}
        {activeTab === "traces" && <TracesTab traces={traces} />}
      </div>
    </div>
  );
}

function ReportTab({
  report,
  taskStatus,
}: {
  report: Report | null;
  taskStatus: string;
}) {
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
  const sections = (content.sections ?? []) as Array<{
    title: string;
    content: string;
  }>;
  const executiveSummary = (content.executive_summary ?? "") as string;

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">{report.title}</h2>
        <p className="text-xs text-gray-400 mt-1">
          生成于 {formatTime(report.created_at)}
        </p>
      </div>

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
        <div key={i} className="space-y-2">
          <h3 className="text-base font-semibold text-gray-900">
            {sec.title}
          </h3>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">
            {sec.content}
          </p>
        </div>
      ))}

      {sections.length === 0 && !executiveSummary && (
        <p className="text-sm text-gray-500">报告内容为空</p>
      )}
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
    <div className="space-y-3">
      {traces.map((t) => {
        const statusCls =
          t.status === "completed"
            ? "text-green-600"
            : t.status === "failed"
              ? "text-red-600"
              : "text-blue-600";
        return (
          <div
            key={t.id}
            className="bg-white rounded-xl p-4 shadow-sm border border-gray-100"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-gray-400" />
                <span className="text-sm font-semibold text-gray-900">
                  {t.agent_name}
                </span>
              </div>
              <span className={`text-xs font-medium ${statusCls}`}>
                {t.status}
              </span>
            </div>
            <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
              {t.total_duration != null && (
                <span>耗时: {t.total_duration.toFixed(2)}s</span>
              )}
              {t.total_tokens != null && (
                <span>Tokens: {t.total_tokens}</span>
              )}
              <span>事件数: {Array.isArray(t.events) ? t.events.length : 0}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
