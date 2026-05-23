import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, X } from "lucide-react";
import { taskApi } from "../api/client";

export default function TaskCreate() {
  const navigate = useNavigate();
  const [industry, setIndustry] = useState("");
  const [targetProduct, setTargetProduct] = useState("");
  const [competitors, setCompetitors] = useState<string[]>([""]);
  const [loading, setLoading] = useState(false);

  const addCompetitor = () => setCompetitors([...competitors, ""]);
  const removeCompetitor = (i: number) =>
    setCompetitors(competitors.filter((_, idx) => idx !== i));
  const updateCompetitor = (i: number, val: string) =>
    setCompetitors(competitors.map((c, idx) => (idx === i ? val : c)));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const resp = await taskApi.create({
        industry,
        target_product: targetProduct,
        competitors: competitors.filter(Boolean),
      });
      navigate(`/`);
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

        {/* Competitors */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            竞品
          </label>
          <div className="space-y-2">
            {competitors.map((c, i) => (
              <div key={i} className="flex gap-2">
                <input
                  type="text"
                  value={c}
                  onChange={(e) => updateCompetitor(i, e.target.value)}
                  placeholder={`竞品 ${i + 1}`}
                  className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
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
