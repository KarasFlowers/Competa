import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, X, ChevronDown, ChevronUp } from "lucide-react";
import { taskApi, type CompetitorInput } from "../api/client";

interface CompetitorForm {
  name: string;
  category: string;
  website: string;
  notes: string;
  expanded: boolean;
}

const emptyCompetitor = (): CompetitorForm => ({
  name: "",
  category: "direct",
  website: "",
  notes: "",
  expanded: false,
});

export default function TaskCreate() {
  const navigate = useNavigate();
  const [industry, setIndustry] = useState("");
  const [targetProduct, setTargetProduct] = useState("");
  const [ourProductNotes, setOurProductNotes] = useState("");
  const [competitors, setCompetitors] = useState<CompetitorForm[]>([emptyCompetitor()]);
  const [loading, setLoading] = useState(false);

  const addCompetitor = () => setCompetitors([...competitors, emptyCompetitor()]);
  const removeCompetitor = (i: number) =>
    setCompetitors(competitors.filter((_, idx) => idx !== i));
  const updateCompetitor = (i: number, field: keyof CompetitorForm, val: string | boolean) =>
    setCompetitors(competitors.map((c, idx) => (idx === i ? { ...c, [field]: val } : c)));
  const toggleExpand = (i: number) =>
    updateCompetitor(i, "expanded", !competitors[i].expanded);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const compPayload: CompetitorInput[] = competitors
        .filter((c) => c.name.trim())
        .map((c) => ({
          name: c.name,
          category: c.category,
          website: c.website || null,
          notes: c.notes,
        }));
      const resp = await taskApi.create({
        industry,
        target_product: targetProduct,
        competitors: compPayload,
        our_product_notes: ourProductNotes,
      });
      navigate(`/tasks/${resp.data.id}`);
    } catch {
      alert("创建失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">新建竞品分析</h1>
      <form onSubmit={handleSubmit} className="space-y-6 bg-white p-6 rounded-xl shadow-sm border border-gray-100">
        {/* Industry */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            行业
          </label>
          <input
            type="text"
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            placeholder="例如：SaaS、电商、金融科技"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Target Product */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            目标产品 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            required
            value={targetProduct}
            onChange={(e) => setTargetProduct(e.target.value)}
            placeholder="你要分析的产品名称"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Our Product Notes */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            我方产品说明
          </label>
          <textarea
            rows={2}
            value={ourProductNotes}
            onChange={(e) => setOurProductNotes(e.target.value)}
            placeholder="简要描述你的产品定位、核心优势、目标用户等（可选）"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Competitors */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            竞品
          </label>
          <div className="space-y-3">
            {competitors.map((c, i) => (
              <div key={i} className="border border-gray-200 rounded-lg p-3">
                <div className="flex gap-2 items-center">
                  <input
                    type="text"
                    value={c.name}
                    onChange={(e) => updateCompetitor(i, "name", e.target.value)}
                    placeholder={`竞品 ${i + 1} 名称`}
                    className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <select
                    value={c.category}
                    onChange={(e) => updateCompetitor(i, "category", e.target.value)}
                    className="rounded-lg border border-gray-300 px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="direct">直接竞品</option>
                    <option value="indirect">间接竞品</option>
                    <option value="substitute">替代品</option>
                  </select>
                  <button
                    type="button"
                    onClick={() => toggleExpand(i)}
                    className="p-2 text-gray-400 hover:text-blue-500 transition-colors"
                    title="展开详情"
                  >
                    {c.expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                  {competitors.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeCompetitor(i)}
                      className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
                {c.expanded && (
                  <div className="mt-3 space-y-2">
                    <input
                      type="url"
                      value={c.website}
                      onChange={(e) => updateCompetitor(i, "website", e.target.value)}
                      placeholder="竞品官网 URL（可选，用于深度抓取）"
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    <textarea
                      rows={2}
                      value={c.notes}
                      onChange={(e) => updateCompetitor(i, "notes", e.target.value)}
                      placeholder="补充说明（销售情报、已知优劣势等）"
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={addCompetitor}
            className="mt-2 inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
          >
            <Plus className="w-4 h-4" /> 添加竞品
          </button>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || !targetProduct.trim()}
          className="w-full py-2.5 px-4 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "创建中…" : "创建分析任务"}
        </button>
      </form>
    </div>
  );
}
