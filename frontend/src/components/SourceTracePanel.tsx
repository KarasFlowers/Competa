import { useEffect, useState } from "react";
import { X, ExternalLink, Link2, ShieldCheck } from "lucide-react";
import type { Source, Claim } from "../api/client";
import { externalHref } from "../api/client";
import MarkdownContent from "./MarkdownContent";
import { ReliabilityBadge } from "./ReliabilityBadge";

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

interface SourceTracePanelProps {
  source: Source;
  claims: Claim[];
  onClose: () => void;
}

export default function SourceTracePanel({ source, claims, onClose }: SourceTracePanelProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Trigger slide-in after mount
    requestAnimationFrame(() => setVisible(true));
  }, []);

  // Find claims that cite this source
  const citingClaims = claims.filter((c) =>
    c.evidence_ids?.includes(source.id)
  );
  const excerpt = source.curated_excerpt?.trim() || source.content_snippet?.trim() || "";

  return (
    <div
      className={`fixed top-0 right-0 h-full w-96 bg-white shadow-2xl border-l border-gray-200 z-50 transform transition-transform duration-300 ease-out flex flex-col ${visible ? "translate-x-0" : "translate-x-full"}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
          <Link2 className="w-4 h-4 text-blue-500" />
          信息溯源
        </h3>
        <button
          onClick={onClose}
          aria-label="关闭溯源面板"
          className="text-gray-400 hover:text-gray-600 p-1 rounded hover:bg-gray-100"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Source info */}
        <div className="space-y-3">
          <h4 className="font-medium text-gray-900 text-sm leading-snug">
            {source.title || "来源详情"}
          </h4>

          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 bg-gray-100 rounded text-xs text-gray-600">
              {source.type}
            </span>
            {source.reliability_score != null && (
              <ReliabilityBadge score={source.reliability_score} />
            )}
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                source.included_in_analysis ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
              }`}
            >
              {source.included_in_analysis ? "已纳入分析" : "未纳入分析"}
            </span>
          </div>

          {source.curation_reason && (
            <div className="rounded-lg bg-gray-50 p-3 text-xs text-gray-700">
              <div className="font-medium text-gray-900">筛选判断</div>
              <div className="mt-1">{getCurationReasonLabel(source.curation_reason)}</div>
            </div>
          )}

          {source.curation_tags?.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {source.curation_tags.slice(0, 5).map((tag) => (
                <span key={tag} className="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-700">
                  {tag}
                </span>
              ))}
            </div>
          )}

          {source.url && (
            <a
              href={externalHref(source.url)}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-xs text-blue-600 hover:underline break-all"
            >
              <ExternalLink className="w-3 h-3 flex-shrink-0" />
              {source.url}
            </a>
          )}

          {excerpt && (
            <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-700 leading-relaxed whitespace-pre-wrap">
              {excerpt}
            </div>
          )}

          <div className="text-xs text-gray-400">
            采集时间: {new Date(source.fetched_at).toLocaleString()}
          </div>
        </div>

        {/* Reverse index: claims citing this source */}
        {citingClaims.length > 0 && (
          <div className="border-t border-gray-100 pt-4">
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5" />
              引用此来源的结论 ({citingClaims.length})
            </h4>
            <ul className="space-y-2">
              {citingClaims.map((claim, i) => (
                <li key={claim.id || i} className="bg-blue-50 border border-blue-100 rounded-lg p-2.5">
                  <MarkdownContent content={claim.content} compact />
                  {claim.confidence !== undefined && (
                    <span className="text-[10px] text-gray-400 mt-1 block">
                      置信度: {(claim.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Trace breadcrumb */}
      <div className="border-t border-gray-100 p-3">
        <div className="flex items-center gap-1 text-[10px] text-gray-400">
          <span>结论</span>
          <span>→</span>
          <span className="text-blue-500">来源</span>
          {source.url && (
            <>
              <span>→</span>
              <a
                href={externalHref(source.url)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-500 hover:underline"
              >
                原文
              </a>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
