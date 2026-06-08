import { useDeferredValue, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  ClipboardList,
  FileSearch,
  FileText,
  FolderKanban,
  MessageSquareText,
  RefreshCw,
  Search,
  Sparkles,
} from "lucide-react";
import { taskApi, type CompetitorInput, type TaskOverviewItem, type TaskOverviewResponse } from "../api/client";

const ACTIVE_STATUSES = new Set([
  "collecting",
  "surveying",
  "interviewing",
  "fieldwork",
  "analyzing",
  "writing",
  "screenshotting",
  "filtering",
  "qa",
  "retrying",
]);

const STATUS_META: Record<string, { label: string; className: string }> = {
  pending: { label: "待启动", className: "bg-gray-100 text-gray-700" },
  collecting: { label: "采集中", className: "bg-blue-100 text-blue-700" },
  surveying: { label: "问卷设计中", className: "bg-cyan-100 text-cyan-700" },
  interviewing: { label: "访谈设计中", className: "bg-teal-100 text-teal-700" },
  fieldwork: { label: "调研执行中", className: "bg-emerald-100 text-emerald-700" },
  analyzing: { label: "分析中", className: "bg-indigo-100 text-indigo-700" },
  writing: { label: "写作中", className: "bg-purple-100 text-purple-700" },
  screenshotting: { label: "截图处理中", className: "bg-fuchsia-100 text-fuchsia-700" },
  filtering: { label: "过滤中", className: "bg-yellow-100 text-yellow-700" },
  qa: { label: "质检中", className: "bg-orange-100 text-orange-700" },
  retrying: { label: "返工中", className: "bg-amber-100 text-amber-700" },
  completed: { label: "已完成", className: "bg-green-100 text-green-700" },
  failed: { label: "失败", className: "bg-red-100 text-red-700" },
};

const STATUS_ORDER = [
  "pending",
  "collecting",
  "surveying",
  "interviewing",
  "fieldwork",
  "analyzing",
  "writing",
  "screenshotting",
  "filtering",
  "qa",
  "retrying",
  "completed",
  "failed",
];

function getCompetitorName(competitor: string | CompetitorInput) {
  return typeof competitor === "string" ? competitor : competitor.name;
}

function getStatusMeta(status: string) {
  return STATUS_META[status] ?? {
    label: status,
    className: "bg-gray-100 text-gray-700",
  };
}

function formatCoverage(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "--";
  }
  return `${(value * 100).toFixed(0)}%`;
}

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

function TaskMetricsStrip({ task }: { task: TaskOverviewItem }) {
  if (!task.metrics) {
    return (
      <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-500">
        当前还没有质量指标，任务运行后会在这里展示证据覆盖率与来源数量。
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <MetricTile label="来源" value={task.metrics.source_count.toString()} />
      <MetricTile label="结论" value={task.metrics.claim_count.toString()} />
      <MetricTile label="覆盖率" value={formatCoverage(task.metrics.evidence_coverage_rate)} />
      <MetricTile label="人工修正" value={task.metrics.manual_correction_count.toString()} />
    </div>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-gray-50 px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-gray-500">{label}</div>
      <div className="mt-1 text-lg font-semibold text-gray-900">{value}</div>
    </div>
  );
}

function ArtifactLinks({ task }: { task: TaskOverviewItem }) {
  const linkClass =
    "inline-flex items-center gap-1 rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:border-blue-200 hover:text-blue-700";

  const passiveClass =
    "inline-flex items-center gap-1 rounded-full border border-dashed border-gray-200 bg-gray-50 px-3 py-1.5 text-xs font-medium text-gray-400";

  return (
    <div className="flex flex-wrap gap-2">
      {task.artifacts.report ? (
        <Link to={`/tasks/${task.id}/report`} className={linkClass}>
          <FileText className="h-3.5 w-3.5" />
          报告
        </Link>
      ) : (
        <span className={passiveClass}>
          <FileText className="h-3.5 w-3.5" />
          报告未生成
        </span>
      )}

      {task.artifacts.traces ? (
        <Link to={`/tasks/${task.id}/traces`} className={linkClass}>
          <Activity className="h-3.5 w-3.5" />
          执行追踪
        </Link>
      ) : (
        <span className={passiveClass}>
          <Activity className="h-3.5 w-3.5" />
          无追踪
        </span>
      )}

      {task.artifacts.survey ? (
        <Link to={`/tasks/${task.id}/survey`} className={linkClass}>
          <ClipboardList className="h-3.5 w-3.5" />
          问卷
        </Link>
      ) : null}

      {task.artifacts.interview ? (
        <Link to={`/tasks/${task.id}/interview`} className={linkClass}>
          <MessageSquareText className="h-3.5 w-3.5" />
          访谈提纲
        </Link>
      ) : null}

      {task.artifacts.analysis ? (
        <span className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700">
          <Sparkles className="h-3.5 w-3.5" />
          结构化分析已生成
        </span>
      ) : null}
    </div>
  );
}

function TaskCard({ task }: { task: TaskOverviewItem }) {
  const statusMeta = getStatusMeta(task.status);
  const competitorNames = task.competitors.map(getCompetitorName).filter(Boolean);
  const notePreview = task.our_product_notes?.trim();

  return (
    <article className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-semibold text-gray-900">{task.target_product}</h2>
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusMeta.className}`}>
              {statusMeta.label}
            </span>
            {ACTIVE_STATUSES.has(task.status) && (
              <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                自动刷新中
              </span>
            )}
          </div>
          <div className="text-sm text-gray-500">
            {task.industry || "未填写行业"} · {competitorNames.length} 个竞品 · 最近更新 {formatTime(task.updated_at)}
          </div>
        </div>

        <Link
          to={`/tasks/${task.id}`}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          打开任务
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {competitorNames.length > 0 ? (
          competitorNames.slice(0, 6).map((name) => (
            <span
              key={name}
              className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700"
            >
              {name}
            </span>
          ))
        ) : (
          <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-500">
            暂无竞品
          </span>
        )}
        {competitorNames.length > 6 && (
          <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-500">
            +{competitorNames.length - 6}
          </span>
        )}
      </div>

      {notePreview ? (
        <div className="mt-5 rounded-2xl border border-blue-100 bg-blue-50/70 px-4 py-3 text-sm leading-6 text-gray-700">
          <span className="font-medium text-blue-900">我方产品备注：</span>
          {notePreview}
        </div>
      ) : null}

      <div className="mt-5">
        <TaskMetricsStrip task={task} />
      </div>

      <div className="mt-5 border-t border-gray-100 pt-5">
        <ArtifactLinks task={task} />
      </div>
    </article>
  );
}

export default function TasksWorkspace() {
  const [overview, setOverview] = useState<TaskOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null);

  const deferredQuery = useDeferredValue(query);

  const loadOverview = async (mode: "initial" | "manual" | "background" = "initial") => {
    if (mode === "initial") {
      setLoading(true);
    }
    if (mode === "manual") {
      setRefreshing(true);
    }

    try {
      const { data } = await taskApi.overview();
      setOverview(data);
      setError("");
      setLastUpdatedAt(new Date().toISOString());
    } catch {
      if (!overview) {
        setError("任务工作台加载失败，请稍后重试。");
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    void loadOverview();
  }, []);

  const activeTaskCount = overview?.stats.active_tasks ?? 0;

  useEffect(() => {
    if (activeTaskCount === 0) {
      return;
    }

    const interval = window.setInterval(() => {
      void loadOverview("background");
    }, 4000);

    return () => window.clearInterval(interval);
  }, [activeTaskCount]);

  const normalizedQuery = deferredQuery.trim().toLowerCase();
  const filteredItems = (overview?.items ?? []).filter((task) => {
    if (selectedStatus !== "all" && task.status !== selectedStatus) {
      return false;
    }

    if (!normalizedQuery) {
      return true;
    }

    const searchableText = [
      task.target_product,
      task.industry,
      task.our_product_notes,
      ...task.competitors.map(getCompetitorName),
    ]
      .join(" ")
      .toLowerCase();

    return searchableText.includes(normalizedQuery);
  });

  const statusEntries = STATUS_ORDER
    .filter((status) => (overview?.stats.status_counts[status] ?? 0) > 0)
    .map((status) => ({
      key: status,
      label: getStatusMeta(status).label,
      count: overview?.stats.status_counts[status] ?? 0,
    }));

  const unmatchedStatusKeys = Object.keys(overview?.stats.status_counts ?? {})
    .filter((status) => !STATUS_ORDER.includes(status))
    .map((status) => ({
      key: status,
      label: status,
      count: overview?.stats.status_counts[status] ?? 0,
    }));

  if (loading && !overview) {
    return (
      <div className="py-16 text-center text-gray-500">
        正在加载任务工作台...
      </div>
    );
  }

  if (error && !overview) {
    return (
      <div className="rounded-3xl border border-red-200 bg-red-50 p-8 text-center">
        <div className="text-lg font-semibold text-red-700">任务工作台暂时不可用</div>
        <p className="mt-2 text-sm text-red-600">{error}</p>
        <button
          onClick={() => void loadOverview("manual")}
          className="mt-4 inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
        >
          <RefreshCw className="h-4 w-4" />
          重新加载
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-[32px] bg-gradient-to-r from-slate-900 via-blue-900 to-cyan-800 p-8 text-white shadow-lg">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-sm font-medium text-blue-100 backdrop-blur">
              <FolderKanban className="h-4 w-4" />
              任务工作台
            </div>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              把每一次竞品分析都放回同一个可追踪的工作面板里
            </h1>
            <p className="text-sm leading-7 text-blue-100 sm:text-base">
              这里集中展示任务状态、报告就绪情况、质量指标和调研产物入口。运行中的任务会自动刷新，方便你在不同阶段随时接回工作。
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => void loadOverview("manual")}
              disabled={refreshing}
              className="inline-flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-70"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              刷新总览
            </button>
            <Link
              to="/tasks/new"
              className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-medium text-slate-900 transition-colors hover:bg-blue-50"
            >
              <FileSearch className="h-4 w-4" />
              新建分析
            </Link>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-3 text-sm text-blue-100">
          <span>当前任务 {overview?.stats.total_tasks ?? 0} 个</span>
          <span className="h-1 w-1 rounded-full bg-blue-200" />
          <span>运行中 {activeTaskCount} 个</span>
          <span className="h-1 w-1 rounded-full bg-blue-200" />
          <span>报告就绪 {overview?.stats.reports_ready ?? 0} 个</span>
          {lastUpdatedAt ? (
            <>
              <span className="h-1 w-1 rounded-full bg-blue-200" />
              <span>上次刷新 {formatTime(lastUpdatedAt)}</span>
            </>
          ) : null}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricTile label="任务总数" value={String(overview?.stats.total_tasks ?? 0)} />
        <MetricTile label="运行中任务" value={String(activeTaskCount)} />
        <MetricTile label="报告就绪" value={String(overview?.stats.reports_ready ?? 0)} />
        <MetricTile
          label="平均证据覆盖"
          value={formatCoverage(overview?.stats.avg_evidence_coverage)}
        />
      </section>

      <section className="rounded-3xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="relative w-full lg:max-w-md">
            <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="搜索任务名、行业、竞品或我方备注"
              className="w-full rounded-2xl border border-gray-200 bg-gray-50 py-3 pl-11 pr-4 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-blue-300 focus:bg-white"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setSelectedStatus("all")}
              className={[
                "rounded-full px-4 py-2 text-sm font-medium transition-colors",
                selectedStatus === "all"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200",
              ].join(" ")}
            >
              全部 ({overview?.stats.total_tasks ?? 0})
            </button>

            {[...statusEntries, ...unmatchedStatusKeys].map((status) => (
              <button
                key={status.key}
                onClick={() => setSelectedStatus(status.key)}
                className={[
                  "rounded-full px-4 py-2 text-sm font-medium transition-colors",
                  selectedStatus === status.key
                    ? "bg-slate-900 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200",
                ].join(" ")}
              >
                {status.label} ({status.count})
              </button>
            ))}
          </div>
        </div>

        {activeTaskCount > 0 ? (
          <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-700">
            检测到 {activeTaskCount} 个任务正在运行，工作台会每 4 秒自动刷新一次。
          </div>
        ) : null}
      </section>

      <section className="space-y-4">
        {filteredItems.length > 0 ? (
          filteredItems.map((task) => <TaskCard key={task.id} task={task} />)
        ) : (
          <div className="rounded-3xl border border-dashed border-gray-300 bg-white p-12 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
              <FolderKanban className="h-7 w-7" />
            </div>
            <h2 className="mt-4 text-xl font-semibold text-gray-900">没有匹配的任务</h2>
            <p className="mt-2 text-sm leading-6 text-gray-500">
              试试更换搜索词或状态筛选；如果你还没有创建任务，可以直接从这里开始一次新的竞品分析。
            </p>
            <Link
              to="/tasks/new"
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
            >
              新建分析
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        )}
      </section>
    </div>
  );
}
