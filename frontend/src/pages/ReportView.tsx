import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  taskApi,
  reportApi,
  sourceApi,
  type Report,
  type Source,
  type ReportSection,
  type Claim,
} from "../api/client";
import { Edit3, Download } from "lucide-react";
import { useToast } from "../components/Toast";

export default function ReportView() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);
  const [error, setError] = useState("");
  const [editingClaim, setEditingClaim] = useState<Claim | null>(null);
  const [editedContent, setEditedContent] = useState("");
  const { toast } = useToast();

  const handleExport = (format: string) => {
    if (!id) return;
    window.open(`/api/reports/${id}/export?format=${format}`, "_blank");
  };

  const refreshReport = () => {
    if (!id) return;
    reportApi.get(id).then((r) => setReport(r.data)).catch(() => setError("Report not found"));
  };

  useEffect(() => {
    if (!id) return;
    refreshReport();
    sourceApi.list(id).then((r) => setSources(r.data)).catch(() => {});
  }, [id]);

  const handleEditClaim = async (e: React.FormEvent) => {
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
      toast("Failed to edit claim", "error");
    }
  };

  const sourceMap = new Map(sources.map((s) => [s.id, s]));

  const handleCiteClick = (sourceId: string) => {
    const src = sourceMap.get(sourceId);
    if (src) setSelectedSource(src);
  };

  if (error) return <div className="p-8 text-red-600">{error}</div>;
  if (!report) return <div className="p-8 text-gray-500">Loading...</div>;

  const content = report.content;

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Back link */}
      <Link to={`/tasks/${id}`} className="text-blue-600 hover:underline text-sm">
        &larr; Back to task
      </Link>

      {/* Report header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">{content.title || report.title}</h1>
        <div className="flex items-center gap-3 mt-2 text-sm text-gray-500">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
            report.status === "final" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"
          }`}>
            {report.status}
          </span>
          <span>{new Date(report.created_at).toLocaleString()}</span>
        </div>
        <div className="flex gap-2 mt-3">
          <button
            onClick={() => handleExport("markdown")}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <Download className="w-3.5 h-3.5" /> Markdown
          </button>
          <button
            onClick={() => handleExport("docx")}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <Download className="w-3.5 h-3.5" /> Word
          </button>
        </div>
      </div>

      {/* Executive Summary */}
      {content.executive_summary && (
        <section className="bg-blue-50 border border-blue-200 rounded-xl p-5">
          <h2 className="text-lg font-semibold text-blue-900 mb-2">Executive Summary</h2>
          <p className="text-gray-800 leading-relaxed">{content.executive_summary}</p>
        </section>
      )}

      {/* Sections */}
      {content.sections?.map((section, i) => (
        <SectionBlock
          key={i}
          section={section}
          depth={0}
          onCiteClick={handleCiteClick}
          onEditClaim={(claim) => {
            setEditingClaim(claim);
            setEditedContent(claim.content);
          }}
        />
      ))}

      {/* Sources reference list */}
      {sources.length > 0 && (
        <section className="border-t border-gray-200 pt-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Sources</h2>
          <ol className="list-decimal list-inside space-y-2">
            {sources.map((s) => (
              <li key={s.id} className="text-sm">
                <button
                  onClick={() => setSelectedSource(s)}
                  className="text-blue-600 hover:underline"
                >
                  {s.title || s.url || s.id}
                </button>
                <span className="ml-2 text-gray-400 text-xs">[{s.type}]</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* Source Detail Modal */}
      {selectedSource && (
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
    </div>
  );
}

function SectionBlock({
  section,
  depth,
  onCiteClick,
  onEditClaim,
}: {
  section: ReportSection;
  depth: number;
  onCiteClick: (sourceId: string) => void;
  onEditClaim: (claim: Claim) => void;
}) {
  const HeadingTag = depth === 0 ? "h2" : "h3";
  const headingClass = depth === 0
    ? "text-xl font-semibold text-gray-900 mb-2"
    : "text-lg font-medium text-gray-800 mb-1";

  return (
    <section className="space-y-3">
      <HeadingTag className={headingClass}>{section.title}</HeadingTag>
      {section.content && (
        <p className="text-gray-700 leading-relaxed">{section.content}</p>
      )}
      {section.claims && section.claims.length > 0 && (
        <ul className="space-y-2 ml-4">
          {section.claims.map((claim, j) => (
            <ClaimBlock key={j} claim={claim} onCiteClick={onCiteClick} onEditClaim={onEditClaim} />
          ))}
        </ul>
      )}
      {section.subsections?.map((sub, k) => (
        <SectionBlock key={k} section={sub} depth={depth + 1} onCiteClick={onCiteClick} onEditClaim={onEditClaim} />
      ))}
    </section>
  );
}

function ClaimBlock({
  claim,
  onCiteClick,
  onEditClaim,
}: {
  claim: Claim;
  onCiteClick: (sourceId: string) => void;
  onEditClaim: (claim: Claim) => void;
}) {
  return (
    <li className="bg-gray-50 border border-gray-200 rounded-lg p-3 group relative pr-10">
      <p className="text-gray-800 text-sm">{claim.content}</p>
      
      {claim.id && (
        <button
          onClick={() => onEditClaim(claim)}
          className="absolute right-3 top-3 text-gray-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity"
          title="修正结论"
        >
          <Edit3 className="w-4 h-4" />
        </button>
      )}
      {claim.evidence_ids && claim.evidence_ids.length > 0 && (
        <div className="flex gap-1 mt-2">
          {claim.evidence_ids.map((eid) => (
            <button
              key={eid}
              onClick={() => onCiteClick(eid)}
              className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded hover:bg-blue-200 transition"
              title={`Source: ${eid}`}
            >
              [{eid.slice(0, 6)}]
            </button>
          ))}
        </div>
      )}
      {claim.confidence !== undefined && (
        <span className="text-xs text-gray-400 mt-1 block">
          Confidence: {(claim.confidence * 100).toFixed(0)}%
        </span>
      )}
    </li>
  );
}

function SourceModal({ source, onClose }: { source: Source; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-xl max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6 space-y-4">
          <div className="flex justify-between items-start">
            <h3 className="text-lg font-semibold text-gray-900">{source.title || "Source Detail"}</h3>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
          </div>

          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium text-gray-600">Type:</span>{" "}
              <span className="px-2 py-0.5 bg-gray-100 rounded text-xs">{source.type}</span>
            </div>
            {source.url && (
              <div>
                <span className="font-medium text-gray-600">URL:</span>{" "}
                <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline break-all">
                  {source.url}
                </a>
              </div>
            )}
            <div>
              <span className="font-medium text-gray-600">Fetched:</span>{" "}
              {new Date(source.fetched_at).toLocaleString()}
            </div>
          </div>

          {source.content_snippet && (
            <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700 whitespace-pre-wrap">
              {source.content_snippet}
            </div>
          )}

          <div className="text-xs text-gray-400">ID: {source.id}</div>
        </div>
      </div>
    </div>
  );
}
