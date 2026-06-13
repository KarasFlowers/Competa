import { Suspense, lazy, useEffect, useState, type ComponentType } from "react";
import { Link, useParams } from "react-router-dom";
import {
  demoApi,
  externalHref,
  type DemoScenarioDetail,
  type DemoSource,
  type ReportSection,
  type Claim,
} from "../api/client";
import { ArrowLeft, Clock, FileText, BarChart3, ShieldCheck } from "lucide-react";
import MarkdownContent from "../components/MarkdownContent";
import { ReliabilityBadge } from "../components/ReliabilityBadge";
import type { AnalysisData } from "../api/client";

const LazyComparisonMatrix = lazy(() => import("../components/ComparisonMatrix"));

function SectionLoading({ label }: { label: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-8 text-center text-sm text-gray-500">
      {label}
    </div>
  );
}

export default function DemoView() {
  const { scenarioId } = useParams<{ scenarioId: string }>();
  const [scenario, setScenario] = useState<DemoScenarioDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!scenarioId) return;
    demoApi
      .get(scenarioId)
      .then((r) => setScenario(r.data))
      .catch(() => setError("示例场景未找到"));
  }, [scenarioId]);

  if (error) return <div className="p-8 text-red-600">{error}</div>;
  if (!scenario) return <div className="p-8 text-gray-500">加载示例中...</div>;

  const sourceMap = new Map<string, DemoSource>(scenario.sources.map((s) => [s.id, s]));

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <Link to="/" className="text-blue-600 hover:underline text-sm inline-flex items-center gap-1">
        <ArrowLeft className="w-4 h-4" /> 返回首页
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded">示例</span>
            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">{scenario.industry}</span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900">{scenario.report.title || scenario.name}</h1>
          <p className="mt-1 text-sm text-gray-500">
            目标产品：{scenario.target_product}，对比 {scenario.competitors.map((c) => c.name).join("、")}
          </p>
        </div>
        <Link
          to="/tasks/new"
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
        >
          创建我的分析
        </Link>
      </div>

      {/* Metrics bar */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard icon={FileText} label="分析证据" value={scenario.metrics.source_count} />
        <MetricCard icon={BarChart3} label="结论数" value={scenario.metrics.claim_count} />
        <MetricCard icon={ShieldCheck} label="证据覆盖率" value={`${(scenario.metrics.evidence_coverage_rate * 100).toFixed(0)}%`} />
        <MetricCard icon={Clock} label="总耗时" value={`${scenario.traces.reduce((s, t) => s + (t.total_duration ?? 0), 0).toFixed(1)}s`} />
      </div>

      {/* Agent trace timeline */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">执行轨迹</h2>
        <div className="flex items-center gap-2 overflow-x-auto pb-2">
          {scenario.traces.map((trace, i) => {
            const agentColors: Record<string, string> = {
              collector: "bg-blue-500",
              survey: "bg-cyan-500",
              interview: "bg-teal-500",
              fieldwork: "bg-emerald-500",
              analyst: "bg-purple-500",
              writer: "bg-green-500",
              filter: "bg-yellow-500",
              qa: "bg-red-500",
            };
            const color = agentColors[trace.agent_name] || "bg-gray-500";
            return (
              <div key={i} className="flex items-center gap-2 min-w-0">
                <div className="flex flex-col items-center">
                  <div className={`w-8 h-8 rounded-full ${color} flex items-center justify-center text-white text-xs font-bold`}>
                    {trace.agent_name.slice(0, 2).toUpperCase()}
                  </div>
                  <span className="text-xs text-gray-500 mt-1">{trace.agent_name}</span>
                  <span className="text-xs text-gray-400">{trace.total_duration?.toFixed(1)}s</span>
                </div>
                {i < scenario.traces.length - 1 && (
                  <div className="w-8 h-0.5 bg-gray-300 flex-shrink-0" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Executive Summary */}
      {scenario.report.executive_summary && (
        <section className="bg-blue-50 border border-blue-200 rounded-xl p-5">
          <h2 className="text-lg font-semibold text-blue-900 mb-2">执行摘要</h2>
          <MarkdownContent content={scenario.report.executive_summary} />
        </section>
      )}

      {/* Comparison Matrix + SWOT (structured analysis) */}
      {scenario.analysis && (
        <Suspense fallback={<SectionLoading label="正在加载结构化分析视图..." />}>
          <LazyComparisonMatrix analysis={scenario.analysis as AnalysisData} />
        </Suspense>
      )}

      {/* Report sections */}
      {scenario.report.sections?.map((section, i) => (
        <DemoSectionBlock
          key={i}
          section={section}
          depth={0}
          sourceMap={sourceMap}
        />
      ))}

      {/* Sources list */}
      {scenario.sources.length > 0 && (
        <section className="border-t border-gray-200 pt-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">分析证据</h2>
          <ol className="list-decimal list-inside space-y-2">
            {scenario.sources.map((s) => (
              <li key={s.id} className="text-sm flex items-center gap-2">
                {s.url ? (
                  <a href={externalHref(s.url)} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                    {s.title || s.url}
                  </a>
                ) : (
                  <span>{s.title || s.id}</span>
                )}
                <span className="text-gray-400 text-xs">[{s.type}]</span>
                {s.reliability_score != null && (
                  <ReliabilityBadge score={s.reliability_score} />
                )}
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

function MetricCard({ icon: Icon, label, value }: { icon: ComponentType<{ className?: string }>; label: string; value: string | number }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
      <Icon className="w-5 h-5 text-blue-600" />
      <div>
        <div className="text-xs text-gray-500">{label}</div>
        <div className="text-lg font-bold text-gray-900">{value}</div>
      </div>
    </div>
  );
}

function DemoSectionBlock({
  section,
  depth,
  sourceMap,
}: {
  section: ReportSection;
  depth: number;
  sourceMap: Map<string, DemoSource>;
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
            <DemoClaimBlock key={j} claim={claim} sourceMap={sourceMap} />
          ))}
        </ul>
      )}
      {section.subsections?.map((sub, k) => (
        <DemoSectionBlock key={k} section={sub} depth={depth + 1} sourceMap={sourceMap} />
      ))}
    </section>
  );
}

function DemoClaimBlock({ claim, sourceMap }: { claim: Claim; sourceMap: Map<string, DemoSource> }) {
  return (
    <li className="bg-gray-50 border border-gray-200 rounded-lg p-3">
      <MarkdownContent content={claim.content} compact />
      {claim.evidence_ids && claim.evidence_ids.length > 0 && (
        <div className="flex gap-1 mt-2">
          {claim.evidence_ids.map((eid) => {
            const src = sourceMap.get(eid);
            return (
              <span
                key={eid}
                className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded"
                title={src ? `${src.title} (${src.type})` : eid}
              >
                [{src?.title?.slice(0, 12) || eid.slice(0, 6)}]
              </span>
            );
          })}
        </div>
      )}
      {claim.confidence !== undefined && (
        <span className="text-xs text-gray-400 mt-1 block">
          置信度: {(claim.confidence * 100).toFixed(0)}%
        </span>
      )}
    </li>
  );
}

