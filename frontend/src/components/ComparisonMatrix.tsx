import type {
  AnalysisData,
  FeatureTree,
  FeatureNode,
  PricingModel,
  Persona,
  SWOTAnalysis,
} from "../api/client";

// Status → cell rendering for the feature comparison matrix.
const STATUS_CELL: Record<string, { label: string; cls: string }> = {
  supported: { label: "✓", cls: "bg-green-100 text-green-700" },
  partial: { label: "◐", cls: "bg-yellow-100 text-yellow-700" },
  missing: { label: "✗", cls: "bg-red-50 text-red-400" },
};

// SWOT category → quadrant styling.
const SWOT_META: Record<string, { title: string; cls: string; head: string }> = {
  strength: { title: "优势 (S)", cls: "bg-green-50 border-green-200", head: "text-green-800" },
  weakness: { title: "劣势 (W)", cls: "bg-red-50 border-red-200", head: "text-red-800" },
  opportunity: { title: "机会 (O)", cls: "bg-blue-50 border-blue-200", head: "text-blue-800" },
  threat: { title: "威胁 (T)", cls: "bg-amber-50 border-amber-200", head: "text-amber-800" },
};

export default function ComparisonMatrix({
  analysis,
  onCiteClick,
  sourceIndexMap,
}: {
  analysis: AnalysisData;
  onCiteClick?: (sourceId: string) => void;
  sourceIndexMap?: Map<string, number>;
}) {
  const hasFeatures = analysis.feature_trees?.length > 0;
  const hasPricing = analysis.pricing_models?.some((p) => p.tiers?.length > 0);
  const hasPersonas = analysis.personas?.length > 0;
  const hasSwot = analysis.swot_analyses?.some((s) => s.items?.length > 0);

  if (!hasFeatures && !hasPricing && !hasPersonas && !hasSwot) return null;

  return (
    <div className="space-y-8">
      {hasFeatures && <FeatureMatrix trees={analysis.feature_trees} />}
      {hasPricing && <PricingTable models={analysis.pricing_models} />}
      {hasSwot && (
        <SWOTGrid
          analyses={analysis.swot_analyses}
          onCiteClick={onCiteClick}
          sourceIndexMap={sourceIndexMap}
        />
      )}
      {hasPersonas && <PersonaCards personas={analysis.personas} />}
    </div>
  );
}

// --- Feature comparison matrix: features as rows, products as columns ---
function FeatureMatrix({ trees }: { trees: FeatureTree[] }) {
  // Union of all top-level feature names across products, preserving order.
  const featureNames: string[] = [];
  for (const t of trees) {
    for (const n of t.root_nodes || []) {
      if (n.name && !featureNames.includes(n.name)) featureNames.push(n.name);
    }
  }
  // product → feature name → node
  const lookup = new Map<string, Map<string, FeatureNode>>();
  for (const t of trees) {
    const m = new Map<string, FeatureNode>();
    for (const n of t.root_nodes || []) m.set(n.name, n);
    lookup.set(t.product_name, m);
  }

  return (
    <section>
      <h3 className="text-lg font-semibold text-gray-900 mb-3">功能对比矩阵</h3>
      <div className="overflow-x-auto rounded-xl border border-gray-200">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="bg-gray-50">
              <th className="text-left px-4 py-2.5 font-medium text-gray-600 sticky left-0 bg-gray-50">功能维度</th>
              {trees.map((t) => (
                <th key={t.product_name} className="px-4 py-2.5 font-semibold text-gray-800 text-center whitespace-nowrap">
                  {t.product_name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {featureNames.map((fname, ri) => (
              <tr key={fname} className={ri % 2 ? "bg-white" : "bg-gray-50/40"}>
                <td className="px-4 py-2.5 font-medium text-gray-700 sticky left-0 bg-inherit">{fname}</td>
                {trees.map((t) => {
                  const node = lookup.get(t.product_name)?.get(fname);
                  const meta = STATUS_CELL[node?.status || "missing"] || STATUS_CELL.missing;
                  return (
                    <td key={t.product_name} className="px-4 py-2.5 text-center">
                      <span
                        className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${meta.cls}`}
                        title={node?.description || node?.status || "missing"}
                      >
                        {meta.label}
                      </span>
                      {node?.description && (
                        <div className="text-[11px] text-gray-400 mt-0.5 max-w-[140px] mx-auto leading-tight">{node.description}</div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex gap-4 mt-2 text-xs text-gray-400">
        <span><span className="text-green-600 font-bold">✓</span> 支持</span>
        <span><span className="text-yellow-600 font-bold">◐</span> 部分支持</span>
        <span><span className="text-red-400 font-bold">✗</span> 不支持</span>
      </div>
    </section>
  );
}

// --- Pricing comparison: tiers laid out per product ---
function PricingTable({ models }: { models: PricingModel[] }) {
  const active = models.filter((m) => m.tiers?.length > 0);
  return (
    <section>
      <h3 className="text-lg font-semibold text-gray-900 mb-3">定价模型对比</h3>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {active.map((m) => (
          <div key={m.product_name} className="rounded-xl border border-gray-200 overflow-hidden">
            <div className="bg-gray-50 px-4 py-2.5 border-b border-gray-200">
              <div className="font-semibold text-gray-800">{m.product_name}</div>
              {m.model_type && <div className="text-xs text-gray-400 mt-0.5">{m.model_type}</div>}
            </div>
            <div className="divide-y divide-gray-100">
              {m.tiers.map((t, i) => (
                <div key={i} className="px-4 py-3">
                  <div className="flex items-baseline justify-between">
                    <span className="font-medium text-gray-700 text-sm">{t.name}</span>
                    <span className="text-sm text-gray-900 font-semibold">
                      {t.price > 0 ? `${t.currency || "USD"} ${t.price}/${t.period || "mo"}` : "免费"}
                    </span>
                  </div>
                  {t.features && t.features.length > 0 && (
                    <ul className="mt-1.5 space-y-0.5">
                      {t.features.slice(0, 4).map((f, fi) => (
                        <li key={fi} className="text-xs text-gray-500 flex gap-1">
                          <span className="text-green-500">·</span>{f}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// --- SWOT quadrants, one block per product ---
function SWOTGrid({
  analyses,
  onCiteClick,
  sourceIndexMap,
}: {
  analyses: SWOTAnalysis[];
  onCiteClick?: (sourceId: string) => void;
  sourceIndexMap?: Map<string, number>;
}) {
  const order = ["strength", "weakness", "opportunity", "threat"];
  return (
    <section>
      <h3 className="text-lg font-semibold text-gray-900 mb-3">SWOT 分析</h3>
      <div className="space-y-6">
        {analyses.filter((a) => a.items?.length > 0).map((a) => {
          const byCat = new Map<string, typeof a.items>();
          for (const it of a.items) {
            const arr = byCat.get(it.category) || [];
            arr.push(it);
            byCat.set(it.category, arr);
          }
          return (
            <div key={a.product_name}>
              <div className="font-medium text-gray-700 mb-2">{a.product_name}</div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {order.map((cat) => {
                  const meta = SWOT_META[cat];
                  const items = byCat.get(cat) || [];
                  if (!meta) return null;
                  return (
                    <div key={cat} className={`rounded-xl border p-3 ${meta.cls}`}>
                      <div className={`text-sm font-semibold mb-1.5 ${meta.head}`}>{meta.title}</div>
                      <ul className="space-y-1.5">
                        {items.length === 0 && <li className="text-xs text-gray-400">—</li>}
                        {items.map((it, i) => (
                          <li key={i} className="text-sm text-gray-700 flex gap-1">
                            <span>{it.content}</span>
                            {it.evidence_ids?.map((eid) => (
                              <button
                                key={eid}
                                onClick={() => onCiteClick?.(eid)}
                                disabled={!onCiteClick}
                                className="text-[11px] text-blue-600 hover:underline font-medium align-super disabled:text-gray-400 disabled:no-underline"
                                title={`溯源: ${eid}`}
                              >
                                [{sourceIndexMap?.get(eid) ?? eid.slice(0, 4)}]
                              </button>
                            ))}
                          </li>
                        ))}
                      </ul>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// --- User persona cards ---
function PersonaCards({ personas }: { personas: Persona[] }) {
  return (
    <section>
      <h3 className="text-lg font-semibold text-gray-900 mb-3">用户画像</h3>
      <div className="grid gap-4 md:grid-cols-2">
        {personas.map((p, i) => (
          <div key={i} className="rounded-xl border border-gray-200 p-4 space-y-2">
            <div className="font-semibold text-gray-800">{p.segment_name}</div>
            {p.demographics && <div className="text-xs text-gray-500">{p.demographics}</div>}
            {p.pain_points && p.pain_points.length > 0 && (
              <div>
                <div className="text-xs font-medium text-red-600 mb-0.5">痛点</div>
                <ul className="text-sm text-gray-600 space-y-0.5">
                  {p.pain_points.map((pp, j) => (
                    <li key={j} className="flex gap-1"><span className="text-red-400">·</span>{pp}</li>
                  ))}
                </ul>
              </div>
            )}
            {p.needs && p.needs.length > 0 && (
              <div>
                <div className="text-xs font-medium text-green-600 mb-0.5">需求</div>
                <ul className="text-sm text-gray-600 space-y-0.5">
                  {p.needs.map((n, j) => (
                    <li key={j} className="flex gap-1"><span className="text-green-400">·</span>{n}</li>
                  ))}
                </ul>
              </div>
            )}
            {p.product_usage_patterns && (
              <div className="text-xs text-gray-400 pt-1 border-t border-gray-100">{p.product_usage_patterns}</div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}




