import { Suspense, lazy, useEffect, useState, type FormEvent } from "react";
import { useParams, Link } from "react-router-dom";
import {
  taskApi,
  reportApi,
  sourceApi,
  analysisApi,
  externalHref,
  type Report,
  type ReportExportFormat,
  type Source,
  type ReportSection,
  type Claim,
  type AnalysisData,
  type CurationSummary,
} from "../api/client";
import { Edit3, Download } from "lucide-react";
import MarkdownContent from "../components/MarkdownContent";
import { useToast } from "../components/Toast";
import { ReliabilityBadge } from "../components/ReliabilityBadge";
import SourceTracePanel from "../components/SourceTracePanel";

const LazyComparisonMatrix = lazy(() => import("../components/ComparisonMatrix"));

const REPORT_STATUS_LABELS: Record<string, string> = {
  final: "最终稿",
  draft: "草稿",
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

function hasCurationMetadata(source: Source) {
  return Boolean(
    source.included_in_analysis
    || source.curation_reason
    || source.curated_excerpt
    || source.curation_tags?.length,
  );
}

function formatReliability(score?: number | null) {
  if (score == null) {
    return "--";
  }
  return `${(score * 100).toFixed(0)}%`;
}

function getSourceExcerpt(source: Source) {
  return source.curated_excerpt?.trim() || source.content_snippet?.trim() || "";
}

function SectionLoading({ label }: { label: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-8 text-center text-sm text-gray-500">
      {label}
    </div>
  );
}

export default function ReportView() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);
  const [highlightedSourceId, setHighlightedSourceId] = useState<string | null>(null);
  const [tracePanelOpen, setTracePanelOpen] = useState(false);
  const [error, setError] = useState("");
  const [editingClaim, setEditingClaim] = useState<Claim | null>(null);
  const [editedContent, setEditedContent] = useState("");
  const [taskMeta, setTaskMeta] = useState<{
    focus_areas: string[];
    manual_correction_count: number;
    last_curation_summary: CurationSummary;
  } | null>(null);
  const { toast } = useToast();

  const handleExport = (format: ReportExportFormat) => {
    if (!id) return;
    window.open(reportApi.exportUrl(id, format), "_blank");
  };

  const refreshReport = () => {
    if (!id) return;
    reportApi.get(id).then((r) => setReport(r.data)).catch(() => setError("报告未找到"));
  };

  useEffect(() => {
    if (!id) return;
    refreshReport();
    taskApi.get(id).then((r) => setTaskMeta({
      focus_areas: r.data.focus_areas ?? [],
      manual_correction_count: r.data.manual_correction_count ?? 0,
      last_curation_summary: r.data.last_curation_summary ?? {},
    })).catch(() => setTaskMeta(null));
    sourceApi.list(id).then((r) => setSources(r.data)).catch(() => {});
    analysisApi.get(id).then((r) => setAnalysis(r.data)).catch(() => setAnalysis(null));
  }, [id]);

  const handleEditClaim = async (e: FormEvent) => {
    e.preventDefault();
    if (!id || !editingClaim?.id) return;
    
    try {
      await taskApi.submitCorrection(id, {
        correction_type: "edit_claim",
        data: {
          claim_id: editingClaim.id,
          content: editedContent
        }
      });
      setEditingClaim(null);
      toast("结论已修正", "success");
      refreshReport();
    } catch (err) {
      toast("修正结论失败", "error");
    }
  };

  const sourceMap = new Map(sources.map((s) => [s.id, s]));
  const hasSourceCuration = sources.some(hasCurationMetadata);
  const includedSources = hasSourceCuration ? sources.filter((source) => source.included_in_analysis) : sources;
  const excludedSources = hasSourceCuration ? sources.filter((source) => !source.included_in_analysis) : [];
  const citationSources = hasSourceCuration && includedSources.length > 0 ? includedSources : sources;
  const sourceIndexMap = new Map(citationSources.map((s, i) => [s.id, i + 1]));

  const handleCiteClick = (sourceId: string) => {
    const src = sourceMap.get(sourceId);
    if (src) {
      setSelectedSource(src);
      setTracePanelOpen(true);
      setHighlightedSourceId(sourceId);
      // Scroll to source in the list
      setTimeout(() => {
        const el = document.getElementById(`source-${sourceId}`);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 100);
    }
  };

  if (error) return <div className="p-8 text-red-600">{error}</div>;
  if (!report) return <div className="p-8 text-gray-500">加载报告中...</div>;

  const content = report.content;
  const reportStatusLabel = REPORT_STATUS_LABELS[report.status] ?? report.status;
  const curationSummary = taskMeta?.last_curation_summary ?? {};
  const removedReasons = Object.entries(curationSummary.removed_reasons ?? {}).sort((a, b) => b[1] - a[1]);

  // Collect all claims for reverse index in trace panel
  const allClaims: Claim[] = [];
  const collectClaims = (sections: ReportSection[]) => {
    for (const s of sections) {
      if (s.claims) allClaims.push(...s.claims);
      if (s.subsections) collectClaims(s.subsections);
    }
  };
  if (content.sections) collectClaims(content.sections);

  return (
    <div className={`max-w-4xl mx-auto p-6 space-y-6 ${tracePanelOpen ? "mr-96" : ""} transition-all duration-300`}>
      {/* Back link */}
      <Link to={`/tasks/${id}`} className="inline-flex items-center gap-1 text-blue-600 hover:underline text-sm">
        <span aria-hidden="true">&larr;</span> 返回任务
      </Link>

      {/* Report header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">{content.title || report.title}</h1>
        <div className="flex items-center gap-3 mt-2 text-sm text-gray-500">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
            report.status === "final" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"
          }`}>
            {reportStatusLabel}
          </span>
          <span>{new Date(report.created_at).toLocaleString()}</span>
        </div>
        {taskMeta && (taskMeta.focus_areas.length > 0 || taskMeta.manual_correction_count > 0 || hasCurationSummary(taskMeta.last_curation_summary)) && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {taskMeta.focus_areas.map((area) => (
              <span key={area} className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                {area}
              </span>
            ))}
            {taskMeta.manual_correction_count > 0 && (
              <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
                人工修正 {taskMeta.manual_correction_count} 次
              </span>
            )}
            {hasCurationSummary(taskMeta.last_curation_summary) && (
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                证据筛选 {taskMeta.last_curation_summary.kept_count ?? 0}/{taskMeta.last_curation_summary.input_count ?? 0}
              </span>
            )}
          </div>
        )}
        <div className="flex gap-2 mt-3">
          <button
            onClick={() => handleExport("markdown")}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <Download className="w-3.5 h-3.5" /> 导出 Markdown
          </button>
          <button
            onClick={() => handleExport("docx")}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <Download className="w-3.5 h-3.5" /> 导出 Word
          </button>
        </div>
      </div>

      {/* Executive Summary */}
      {content.executive_summary && (
        <section className="bg-blue-50 border border-blue-200 rounded-xl p-5">
          <h2 className="text-lg font-semibold text-blue-900 mb-2">执行摘要</h2>
          <MarkdownContent content={content.executive_summary} />
        </section>
      )}

      {hasCurationSummary(curationSummary) && (
        <section className="rounded-2xl border border-gray-200 bg-white p-5">
          <h2 className="text-lg font-semibold text-gray-900">本次证据筛选说明</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <SummaryTile label="候选来源" value={String(curationSummary.input_count ?? 0)} />
            <SummaryTile label="纳入分析" value={String(curationSummary.kept_count ?? 0)} />
            <SummaryTile label="已筛除" value={String(curationSummary.removed_count ?? 0)} />
            <SummaryTile label="一手证据" value={String(curationSummary.first_party_count ?? 0)} />
            <SummaryTile label="平均可信度" value={formatReliability(curationSummary.avg_reliability)} />
          </div>
          {removedReasons.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {removedReasons.map(([reason, count]) => (
                <span key={reason} className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
                  {getCurationReasonLabel(reason)} {count} 条
                </span>
              ))}
            </div>
          ) : (
            <p className="mt-4 text-sm text-gray-500">
              本次没有记录明显的筛除原因，说明大多数候选来源都直接进入了分析链路。
            </p>
          )}
        </section>
      )}

      {/* Comparison Matrix + SWOT (structured analysis) */}
      {analysis && (
        <Suspense fallback={<SectionLoading label="正在加载结构化分析视图..." />}>
          <LazyComparisonMatrix
            analysis={analysis}
            onCiteClick={handleCiteClick}
            sourceIndexMap={sourceIndexMap}
          />
        </Suspense>
      )}

      {/* Sections */}
      {content.sections && content.sections.length > 0 ? (
        content.sections.map((section, i) => (
          <SectionBlock
            key={i}
            section={section}
            depth={0}
            onCiteClick={handleCiteClick}
            onEditClaim={(claim) => {
              setEditingClaim(claim);
              setEditedContent(claim.content);
            }}
            sourceIndexMap={sourceIndexMap}
          />
        ))
      ) : (
        <section className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-6 text-sm text-gray-500">
          当前报告还没有正文内容。
        </section>
      )}

      {/* Sources reference list */}
      {citationSources.length > 0 && (
        <section className="border-t border-gray-200 pt-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">
            {hasSourceCuration ? "已纳入分析的来源" : "引用来源"}
          </h2>
          {hasSourceCuration && (
            <p className="mb-3 text-sm text-gray-500">
              报告中的引用编号只对应最终进入分析链路的来源。
            </p>
          )}
          <ol className="list-decimal list-inside space-y-2">
            {citationSources.map((s, idx) => (
              <li
                key={s.id}
                id={`source-${s.id}`}
                className={`rounded-lg border p-3 text-sm transition-colors ${highlightedSourceId === s.id ? "border-blue-200 bg-blue-50" : "border-transparent bg-white"}`}
              >
                <SourceListItem
                  source={s}
                  index={idx + 1}
                  onSelect={handleCiteClick}
                  showIncludedBadge={false}
                />
              </li>
            ))}
          </ol>
        </section>
      )}

      {excludedSources.length > 0 && (
        <section className="rounded-2xl border border-gray-200 bg-gray-50 p-5">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">已筛除 / 未纳入分析的候选来源</h2>
          <p className="text-sm text-gray-500">
            这些来源被系统保留下来用于审计和追溯，但没有进入最终分析与引用链路。
          </p>
          <div className="mt-4 space-y-3">
            {excludedSources.map((source) => (
              <div
                key={source.id}
                id={`source-${source.id}`}
                className={`rounded-xl border p-3 text-sm ${highlightedSourceId === source.id ? "border-blue-200 bg-blue-50" : "border-gray-200 bg-white"}`}
              >
                <SourceListItem
                  source={source}
                  onSelect={handleCiteClick}
                  showIncludedBadge
                />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Source Detail Modal (legacy, kept for non-trace clicks) */}
      {selectedSource && !tracePanelOpen && (
        <SourceModal source={selectedSource} onClose={() => setSelectedSource(null)} />
      )}

      {/* Edit Claim Modal */}
      {editingClaim && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
            <h2 className="text-xl font-bold mb-4">修正结论</h2>
            <form onSubmit={handleEditClaim} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">结论内容</label>
                <textarea
                  required
                  rows={4}
                  className="w-full border rounded-lg p-2"
                  value={editedContent}
                  onChange={(e) => setEditedContent(e.target.value)}
                />
              </div>
              <div className="flex gap-3 justify-end mt-6">
                <button
                  type="button"
                  onClick={() => setEditingClaim(null)}
                  className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  保存修正
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Source Trace Panel (slide-in sidebar) */}
      {tracePanelOpen && selectedSource && (
        <SourceTracePanel
          source={selectedSource}
          claims={allClaims}
          onClose={() => {
            setTracePanelOpen(false);
            setHighlightedSourceId(null);
          }}
        />
      )}
    </div>
  );
}

function SummaryTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-gray-50 p-4">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-gray-900">{value}</div>
    </div>
  );
}

function SectionBlock({
  section,
  depth,
  onCiteClick,
  onEditClaim,
  sourceIndexMap,
}: {
  section: ReportSection;
  depth: number;
  onCiteClick: (sourceId: string) => void;
  onEditClaim: (claim: Claim) => void;
  sourceIndexMap: Map<string, number>;
}) {
  const HeadingTag = depth === 0 ? "h2" : "h3";
  const headingClass = depth === 0
    ? "text-xl font-semibold text-gray-900 mb-2"
    : "text-lg font-medium text-gray-800 mb-1";

  return (
    <section className="space-y-3">
      <HeadingTag className={headingClass}>{section.title}</HeadingTag>
      {section.content && (
        <MarkdownContent content={section.content} />
      )}
      {section.claims && section.claims.length > 0 && (
        <ul className="space-y-2 ml-4">
          {section.claims.map((claim, j) => (
            <ClaimBlock key={j} claim={claim} onCiteClick={onCiteClick} onEditClaim={onEditClaim} sourceIndexMap={sourceIndexMap} />
          ))}
        </ul>
      )}
      {section.subsections?.map((sub, k) => (
        <SectionBlock key={k} section={sub} depth={depth + 1} onCiteClick={onCiteClick} onEditClaim={onEditClaim} sourceIndexMap={sourceIndexMap} />
      ))}
    </section>
  );
}

function ClaimBlock({
  claim,
  onCiteClick,
  onEditClaim,
  sourceIndexMap,
}: {
  claim: Claim;
  onCiteClick: (sourceId: string) => void;
  onEditClaim: (claim: Claim) => void;
  sourceIndexMap: Map<string, number>;
}) {
  return (
    <li className="bg-gray-50 border border-gray-200 rounded-lg p-3 group relative pr-10">
      <div className="space-y-2">
        <MarkdownContent content={claim.content} compact />
        {claim.evidence_ids && claim.evidence_ids.length > 0 && (
          <div className="inline-flex flex-wrap gap-1">
            {claim.evidence_ids.map((eid) => (
              <button
                key={eid}
                onClick={() => onCiteClick(eid)}
                className="text-[11px] text-blue-600 hover:text-blue-800 hover:underline font-medium align-super"
                title={`溯源: ${eid}`}
              >
                [{sourceIndexMap.get(eid) ?? eid.slice(0, 6)}]
              </button>
            ))}
          </div>
        )}
      </div>

      {claim.id && (
        <button
          onClick={() => onEditClaim(claim)}
          className="absolute right-3 top-3 text-gray-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity"
          title="修正结论"
        >
          <Edit3 className="w-4 h-4" />
        </button>
      )}
      {claim.confidence !== undefined && (
        <span className="text-xs text-gray-400 mt-1 block">
          置信度: {(claim.confidence * 100).toFixed(0)}%
        </span>
      )}
    </li>
  );
}

function SourceListItem({
  source,
  index,
  onSelect,
  showIncludedBadge,
}: {
  source: Source;
  index?: number;
  onSelect: (sourceId: string) => void;
  showIncludedBadge: boolean;
}) {
  const excerpt = getSourceExcerpt(source);

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {index ? <span className="text-xs font-mono text-gray-400">[{index}]</span> : null}
        <button
          onClick={() => onSelect(source.id)}
          className="text-left text-blue-600 hover:underline"
        >
          {source.title || source.url || source.id}
        </button>
        <span className="text-xs text-gray-400">[{source.type}]</span>
        {source.reliability_score != null ? (
          <ReliabilityBadge score={source.reliability_score} />
        ) : null}
        {showIncludedBadge ? (
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            source.included_in_analysis ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
          }`}>
            {source.included_in_analysis ? "已纳入分析" : "未纳入分析"}
          </span>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-2 text-xs">
        {source.curation_reason ? (
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-gray-700">
            {getCurationReasonLabel(source.curation_reason)}
          </span>
        ) : null}
        {source.curation_tags?.slice(0, 4).map((tag) => (
          <span key={tag} className="rounded-full bg-blue-50 px-2 py-0.5 text-blue-700">
            {tag}
          </span>
        ))}
      </div>
      {excerpt && (
        <MarkdownContent content={excerpt} compact className="text-sm" />
      )}
    </div>
  );
}

function SourceModal({ source, onClose }: { source: Source; onClose: () => void }) {
  const excerpt = getSourceExcerpt(source);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-xl max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-start">
            <h3 className="text-lg font-semibold text-gray-900">{source.title || "来源详情"}</h3>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
          </div>

          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium text-gray-600">类型：</span>{" "}
              <span className="px-2 py-0.5 bg-gray-100 rounded text-xs">{source.type}</span>
            </div>
            <div>
              <span className="font-medium text-gray-600">状态：</span>{" "}
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                source.included_in_analysis ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
              }`}>
                {source.included_in_analysis ? "已纳入分析" : "未纳入分析"}
              </span>
            </div>
            {source.curation_reason && (
              <div>
                <span className="font-medium text-gray-600">筛选结果：</span>{" "}
                {getCurationReasonLabel(source.curation_reason)}
              </div>
            )}
            {source.url && (
              <div>
                <span className="font-medium text-gray-600">链接：</span>{" "}
                <a href={externalHref(source.url)} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline break-all">
                  {source.url}
                </a>
              </div>
            )}
            {source.reliability_score != null && (
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-600">可信度：</span>{" "}
                <ReliabilityBadge score={source.reliability_score} />
                <span className="text-gray-500 text-xs">({(source.reliability_score * 100).toFixed(0)}%)</span>
              </div>
            )}
            <div>
              <span className="font-medium text-gray-600">采集时间：</span>{" "}
              {new Date(source.fetched_at).toLocaleString()}
            </div>
          </div>

          {source.curation_tags?.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {source.curation_tags.map((tag) => (
                <span key={tag} className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                  {tag}
                </span>
              ))}
            </div>
          )}

          {excerpt && (
            <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700">
              <MarkdownContent content={excerpt} compact />
            </div>
          )}

          <div className="text-xs text-gray-400">ID：{source.id}</div>
        </div>
      </div>
    </div>
  );
}

