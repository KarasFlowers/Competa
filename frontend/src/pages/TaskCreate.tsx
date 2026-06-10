import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Check,
  Globe,
  ListChecks,
  Plus,
  Target,
  Trash2,
  Users,
} from "lucide-react";
import { taskApi, type CompetitorInput } from "../api/client";
import { useToast } from "../components/Toast";

type AnalysisGoalId =
  | "positioning"
  | "feature_strategy"
  | "pricing"
  | "sales_enablement"
  | "market_scan";

interface GoalOption {
  id: AnalysisGoalId;
  title: string;
  description: string;
}

interface CompetitorForm {
  id: string;
  name: string;
  category: "direct" | "indirect" | "substitute";
  website: string;
  notes: string;
}

const GOAL_OPTIONS: GoalOption[] = [
  {
    id: "positioning",
    title: "定位与差异化",
    description: "适合官网改版、品牌信息梳理、核心卖点提炼。",
  },
  {
    id: "feature_strategy",
    title: "功能策略",
    description: "适合决定是否跟进功能、如何排优先级、哪里该补齐短板。",
  },
  {
    id: "pricing",
    title: "定价与包装",
    description: "适合套餐设计、免费策略、价值锚点和价格带判断。",
  },
  {
    id: "sales_enablement",
    title: "销售战卡 / 赢单支持",
    description: "适合售前对比、替换竞品、POC 话术和 objection handling。",
  },
  {
    id: "market_scan",
    title: "赛道扫描",
    description: "适合新市场进入、替代威胁监测、赛道格局快速摸底。",
  },
];

const FOCUS_AREA_OPTIONS = [
  "功能能力",
  "定价与包装",
  "目标客户",
  "典型场景",
  "AI 能力",
  "上手体验",
  "集成与生态",
  "服务与交付",
  "品牌与定位",
  "增长与渠道",
  "数据与安全",
  "替代风险",
];

const CATEGORY_LABELS: Record<CompetitorForm["category"], string> = {
  direct: "直接竞品",
  indirect: "间接竞品",
  substitute: "替代方案",
};

function createCompetitor(): CompetitorForm {
  return {
    id: crypto.randomUUID(),
    name: "",
    category: "direct",
    website: "",
    notes: "",
  };
}

function normalizeWebsite(value: string) {
  const cleaned = value.trim();
  if (!cleaned) {
    return "";
  }
  if (/^https?:\/\//i.test(cleaned)) {
    return cleaned;
  }
  return `https://${cleaned}`;
}

function parseStructuredLines(value: string) {
  return value
    .split(/\n|,|，|;|；/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function dedupeStrings(values: string[]) {
  const seen = new Set<string>();
  const result: string[] = [];

  values.forEach((value) => {
    if (!seen.has(value)) {
      seen.add(value);
      result.push(value);
    }
  });

  return result;
}

function buildResearchBrief(params: {
  goalTitle: string;
  industry: string;
  customerContext: string;
  mustAnswerQuestions: string[];
  focusAreas: string[];
  ourContext: string;
}) {
  const sections: string[] = [];

  const overviewLines = [
    params.goalTitle ? `分析目标：${params.goalTitle}` : "",
    params.industry ? `行业 / 赛道：${params.industry}` : "",
    params.customerContext ? `目标客户 / 关键场景：${params.customerContext}` : "",
  ].filter(Boolean);

  if (overviewLines.length > 0) {
    sections.push(`研究背景\n${overviewLines.map((line) => `- ${line}`).join("\n")}`);
  }

  if (params.focusAreas.length > 0) {
    sections.push(
      `重点关注维度\n${params.focusAreas.map((area) => `- ${area}`).join("\n")}`,
    );
  }

  if (params.mustAnswerQuestions.length > 0) {
    sections.push(
      `必须回答的问题\n${params.mustAnswerQuestions.map((question, index) => `${index + 1}. ${question}`).join("\n")}`,
    );
  }

  if (params.ourContext) {
    sections.push(`内部背景 / 已知判断\n${params.ourContext}`);
  }

  return sections.join("\n\n");
}

function countNonEmptyCompetitors(competitors: CompetitorForm[]) {
  return competitors.filter((competitor) => competitor.name.trim()).length;
}

export default function TaskCreate() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [targetProduct, setTargetProduct] = useState("");
  const [targetWebsite, setTargetWebsite] = useState("");
  const [industry, setIndustry] = useState("");
  const [analysisGoal, setAnalysisGoal] = useState<AnalysisGoalId>("positioning");
  const [customerContext, setCustomerContext] = useState("");
  const [mustAnswerQuestions, setMustAnswerQuestions] = useState("");
  const [ourContext, setOurContext] = useState("");
  const [selectedFocusAreas, setSelectedFocusAreas] = useState<string[]>([
    "功能能力",
    "定价与包装",
  ]);
  const [customFocusAreas, setCustomFocusAreas] = useState("");
  const [competitors, setCompetitors] = useState<CompetitorForm[]>([
    createCompetitor(),
    createCompetitor(),
  ]);
  const [loading, setLoading] = useState(false);

  const goalTitle = GOAL_OPTIONS.find((goal) => goal.id === analysisGoal)?.title ?? "";
  const normalizedFocusAreas = dedupeStrings([
    ...selectedFocusAreas,
    ...parseStructuredLines(customFocusAreas),
  ]);
  const questionItems = parseStructuredLines(mustAnswerQuestions);
  const briefPreview = buildResearchBrief({
    goalTitle,
    industry: industry.trim(),
    customerContext: customerContext.trim(),
    mustAnswerQuestions: questionItems,
    focusAreas: normalizedFocusAreas,
    ourContext: ourContext.trim(),
  });
  const competitorCount = countNonEmptyCompetitors(competitors);
  const inputQualityScore = [
    targetWebsite.trim() ? 1 : 0,
    competitorCount >= 2 ? 1 : 0,
    questionItems.length > 0 ? 1 : 0,
    normalizedFocusAreas.length >= 3 ? 1 : 0,
  ].reduce((sum, value) => sum + value, 0);

  const toggleFocusArea = (area: string) => {
    setSelectedFocusAreas((current) =>
      current.includes(area)
        ? current.filter((item) => item !== area)
        : [...current, area],
    );
  };

  const addCompetitor = () => {
    setCompetitors((current) => [...current, createCompetitor()]);
  };

  const updateCompetitor = (
    id: string,
    field: keyof Omit<CompetitorForm, "id">,
    value: string,
  ) => {
    setCompetitors((current) =>
      current.map((competitor) =>
        competitor.id === id ? { ...competitor, [field]: value } : competitor,
      ),
    );
  };

  const removeCompetitor = (id: string) => {
    setCompetitors((current) => current.filter((competitor) => competitor.id !== id));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);

    try {
      const competitorPayload: CompetitorInput[] = competitors
        .filter((competitor) => competitor.name.trim())
        .map((competitor) => ({
          name: competitor.name.trim(),
          category: competitor.category,
          website: normalizeWebsite(competitor.website) || null,
          notes: competitor.notes.trim(),
        }));

      const response = await taskApi.create({
        industry: industry.trim(),
        target_product: targetProduct.trim(),
        target_website: normalizeWebsite(targetWebsite),
        competitors: competitorPayload,
        focus_areas: normalizedFocusAreas,
        our_product_notes: briefPreview,
      });

      toast("任务已创建。建议先检查 brief，再启动分析。", "success");
      navigate(`/tasks/${response.data.id}`);
    } catch (error: any) {
      toast(error?.response?.data?.detail || "创建失败，请稍后重试。", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-[32px] bg-gradient-to-r from-slate-900 via-cyan-900 to-teal-800 p-8 text-white shadow-lg">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-sm font-medium text-cyan-100 backdrop-blur">
              <Target className="h-4 w-4" />
              研究 brief 驱动的任务创建
            </div>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              先定义这次分析要支持什么决策，再让 Agent 去调研
            </h1>
            <p className="max-w-3xl text-sm leading-7 text-cyan-100 sm:text-base">
              从竞品分析实践看，真正决定输出质量的不是“多填几个字段”，而是把研究目标、目标客户、关键问题和官网锚点提前说清楚。这个页面会把这些输入整理成一份可执行的研究 brief。
            </p>
          </div>

          <div className="rounded-[28px] border border-white/15 bg-white/10 p-5 backdrop-blur">
            <div className="text-sm font-medium text-cyan-100">当前输入完整度</div>
            <div className="mt-3 text-4xl font-semibold text-white">{inputQualityScore}/4</div>
            <div className="mt-4 space-y-2 text-sm text-cyan-100">
              <div className="flex items-center gap-2">
                <Check className={`h-4 w-4 ${targetWebsite.trim() ? "text-emerald-300" : "text-white/40"}`} />
                官网锚点
              </div>
              <div className="flex items-center gap-2">
                <Check className={`h-4 w-4 ${competitorCount >= 2 ? "text-emerald-300" : "text-white/40"}`} />
                至少 2 个竞品
              </div>
              <div className="flex items-center gap-2">
                <Check className={`h-4 w-4 ${questionItems.length > 0 ? "text-emerald-300" : "text-white/40"}`} />
                明确关键问题
              </div>
              <div className="flex items-center gap-2">
                <Check className={`h-4 w-4 ${normalizedFocusAreas.length >= 3 ? "text-emerald-300" : "text-white/40"}`} />
                重点维度足够聚焦
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_360px]">
        <form onSubmit={handleSubmit} className="space-y-6">
          <section className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2 text-gray-900">
              <Globe className="h-5 w-5 text-cyan-600" />
              <h2 className="text-xl font-semibold">分析对象与目标</h2>
            </div>
            <p className="mt-2 text-sm leading-6 text-gray-500">
              这里决定分析的边界。官网和行业信息看似简单，但对后续证据采集质量影响很大。
            </p>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <label className="block">
                <div className="text-sm font-medium text-gray-700">
                  目标产品 <span className="text-red-500">*</span>
                </div>
                <input
                  type="text"
                  required
                  value={targetProduct}
                  onChange={(event) => setTargetProduct(event.target.value)}
                  placeholder="例如：Notion AI、钉钉智能会议纪要、某自家产品"
                  className="mt-2 w-full rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-cyan-300 focus:bg-white"
                />
              </label>

              <label className="block">
                <div className="text-sm font-medium text-gray-700">
                  目标产品官网 <span className="text-amber-600">强烈推荐</span>
                </div>
                <input
                  type="text"
                  value={targetWebsite}
                  onChange={(event) => setTargetWebsite(event.target.value)}
                  placeholder="例如：www.notion.so/product/ai"
                  className="mt-2 w-full rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-cyan-300 focus:bg-white"
                />
                <p className="mt-2 text-xs leading-5 text-gray-500">
                  官方站点通常是最可靠的一手证据源，尤其适合功能、定价和定位分析。
                </p>
              </label>

              <label className="block">
                <div className="text-sm font-medium text-gray-700">行业 / 赛道</div>
                <input
                  type="text"
                  value={industry}
                  onChange={(event) => setIndustry(event.target.value)}
                  placeholder="例如：AI 办公、跨境电商 ERP、企业知识库"
                  className="mt-2 w-full rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-cyan-300 focus:bg-white"
                />
              </label>
            </div>

            <div className="mt-6">
              <div className="text-sm font-medium text-gray-700">这次分析主要服务什么决策</div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {GOAL_OPTIONS.map((goal) => {
                  const selected = goal.id === analysisGoal;

                  return (
                    <button
                      key={goal.id}
                      type="button"
                      onClick={() => setAnalysisGoal(goal.id)}
                      className={[
                        "rounded-2xl border px-4 py-4 text-left transition-colors",
                        selected
                          ? "border-cyan-300 bg-cyan-50 text-cyan-900"
                          : "border-gray-200 bg-gray-50 text-gray-700 hover:border-cyan-200 hover:bg-white",
                      ].join(" ")}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-medium">{goal.title}</div>
                          <div className="mt-2 text-sm leading-6 text-gray-500">
                            {goal.description}
                          </div>
                        </div>
                        {selected ? (
                          <span className="rounded-full bg-cyan-100 px-2 py-1 text-xs font-medium text-cyan-700">
                            当前目标
                          </span>
                        ) : null}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </section>

          <section className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2 text-gray-900">
              <Users className="h-5 w-5 text-cyan-600" />
              <h2 className="text-xl font-semibold">用户视角与分析重点</h2>
            </div>
            <p className="mt-2 text-sm leading-6 text-gray-500">
              竞品分析最容易失真在这里：如果不知道你要服务哪类客户、解决哪种决策，输出就会变成泛泛而谈的“百科式对比”。
            </p>

            <div className="mt-5 space-y-5">
              <label className="block">
                <div className="text-sm font-medium text-gray-700">目标客户 / 关键使用场景</div>
                <textarea
                  rows={3}
                  value={customerContext}
                  onChange={(event) => setCustomerContext(event.target.value)}
                  placeholder="例如：我们在看中大型团队的知识协作场景，重点是销售、交付和项目管理团队的落地体验。"
                  className="mt-2 w-full rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm leading-6 text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-cyan-300 focus:bg-white"
                />
              </label>

              <label className="block">
                <div className="text-sm font-medium text-gray-700">这次必须回答的问题</div>
                <textarea
                  rows={4}
                  value={mustAnswerQuestions}
                  onChange={(event) => setMustAnswerQuestions(event.target.value)}
                  placeholder={"建议一行一个，例如：\n我们和头部竞品相比，真正能放大宣传的差异点是什么？\n用户为什么会在试用后流向替代品？\n竞品的定价锚点有没有压制我们成交？"}
                  className="mt-2 w-full rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm leading-6 text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-cyan-300 focus:bg-white"
                />
                <p className="mt-2 text-xs leading-5 text-gray-500">
                  行业内更有效的 brief 通常不是“分析一下竞品”，而是 3 到 5 个必须回答的问题。
                </p>
              </label>

              <div>
                <div className="text-sm font-medium text-gray-700">重点关注维度</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {FOCUS_AREA_OPTIONS.map((area) => {
                    const selected = selectedFocusAreas.includes(area);

                    return (
                      <button
                        key={area}
                        type="button"
                        onClick={() => toggleFocusArea(area)}
                        className={[
                          "rounded-full px-4 py-2 text-sm font-medium transition-colors",
                          selected
                            ? "bg-cyan-600 text-white"
                            : "bg-gray-100 text-gray-700 hover:bg-gray-200",
                        ].join(" ")}
                      >
                        {area}
                      </button>
                    );
                  })}
                </div>

                <label className="mt-4 block">
                  <div className="text-sm font-medium text-gray-700">补充自定义维度</div>
                  <input
                    type="text"
                    value={customFocusAreas}
                    onChange={(event) => setCustomFocusAreas(event.target.value)}
                    placeholder="例如：招投标能力，私有化部署，客服响应效率"
                    className="mt-2 w-full rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-cyan-300 focus:bg-white"
                  />
                </label>
              </div>
            </div>
          </section>

          <section className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2 text-gray-900">
              <ListChecks className="h-5 w-5 text-cyan-600" />
              <h2 className="text-xl font-semibold">竞品范围</h2>
            </div>
            <p className="mt-2 text-sm leading-6 text-gray-500">
              直接竞品、间接竞品和替代方案最好都覆盖到。行业内部分析里，替代方案常常比“同类产品”更能解释真实流失去向。
            </p>

            <div className="mt-5 space-y-4">
              {competitors.map((competitor, index) => (
                <div key={competitor.id} className="rounded-3xl border border-gray-200 bg-gray-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-medium text-gray-900">竞品 {index + 1}</div>
                      <div className="text-xs text-gray-500">
                        {CATEGORY_LABELS[competitor.category]}
                      </div>
                    </div>

                    {competitors.length > 1 ? (
                      <button
                        type="button"
                        onClick={() => removeCompetitor(competitor.id)}
                        className="inline-flex items-center gap-1 rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:border-red-200 hover:text-red-600"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        删除
                      </button>
                    ) : null}
                  </div>

                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <label className="block">
                      <div className="text-sm font-medium text-gray-700">名称</div>
                      <input
                        type="text"
                        value={competitor.name}
                        onChange={(event) => updateCompetitor(competitor.id, "name", event.target.value)}
                        placeholder="例如：飞书、Slack、Airtable"
                        className="mt-2 w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-cyan-300"
                      />
                    </label>

                    <label className="block">
                      <div className="text-sm font-medium text-gray-700">竞品类型</div>
                      <select
                        value={competitor.category}
                        onChange={(event) =>
                          updateCompetitor(competitor.id, "category", event.target.value)
                        }
                        className="mt-2 w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-900 outline-none transition-colors focus:border-cyan-300"
                      >
                        <option value="direct">直接竞品</option>
                        <option value="indirect">间接竞品</option>
                        <option value="substitute">替代方案</option>
                      </select>
                    </label>

                    <label className="block md:col-span-2">
                      <div className="text-sm font-medium text-gray-700">官网</div>
                      <input
                        type="text"
                        value={competitor.website}
                        onChange={(event) => updateCompetitor(competitor.id, "website", event.target.value)}
                        placeholder="例如：www.notion.so"
                        className="mt-2 w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-cyan-300"
                      />
                    </label>

                    <label className="block md:col-span-2">
                      <div className="text-sm font-medium text-gray-700">补充备注</div>
                      <textarea
                        rows={3}
                        value={competitor.notes}
                        onChange={(event) => updateCompetitor(competitor.id, "notes", event.target.value)}
                        placeholder="例如：销售经常被拿来对比、在大型客户里 win rate 高、某功能最近刚上线。"
                        className="mt-2 w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm leading-6 text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-cyan-300"
                      />
                    </label>
                  </div>
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={addCompetitor}
              className="mt-4 inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:border-cyan-200 hover:text-cyan-700"
            >
              <Plus className="h-4 w-4" />
              添加竞品
            </button>
          </section>

          <section className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-gray-900">内部背景补充</h2>
            <p className="mt-2 text-sm leading-6 text-gray-500">
              这里适合放你们已知但外部公开信息看不到的内容，比如销售反馈、已知优势、最近准备推进的方向和限制条件。
            </p>

            <label className="mt-5 block">
              <div className="text-sm font-medium text-gray-700">研究背景 / 分析 brief 补充</div>
              <textarea
                rows={5}
                value={ourContext}
                onChange={(event) => setOurContext(event.target.value)}
                placeholder={"例如：\n我们最近在推企业版，希望判断是否需要补齐权限和审计能力。\n销售反馈客户经常拿飞书和我们比较，但真正成交障碍可能在实施门槛和培训成本。"}
                className="mt-2 w-full rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm leading-6 text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-cyan-300 focus:bg-white"
              />
            </label>
          </section>

          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              type="submit"
              disabled={loading || !targetProduct.trim()}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-cyan-600 px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-cyan-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "创建中..." : "创建分析任务"}
              <ArrowRight className="h-4 w-4" />
            </button>
            <p className="text-sm leading-6 text-gray-500">
              创建后你可以先检查任务详情中的 brief，再决定是否立即启动完整分析链路。
            </p>
          </div>
        </form>

        <aside className="space-y-4 xl:sticky xl:top-6 xl:self-start">
          <div className="rounded-3xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900">为什么这样设计</h2>
            <div className="mt-3 space-y-3 text-sm leading-6 text-gray-600">
              <p>行业里高质量竞品分析通常先回答“这份分析要支持什么决策”，而不是一上来堆很多泛化字段。</p>
              <p>官网是高价值一手来源，用户场景能限制分析视角，关键问题能把输出从“资料收集”拉到“决策支持”。</p>
              <p>系统会把这些结构化输入回流给采集、问卷、访谈和 fieldwork 环节，而不是只停留在首页表单里。</p>
            </div>
          </div>

          <div className="rounded-3xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900">当前任务摘要</h2>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <SummaryTile label="竞品数量" value={String(competitorCount)} />
              <SummaryTile label="关键问题" value={String(questionItems.length)} />
              <SummaryTile label="重点维度" value={String(normalizedFocusAreas.length)} />
              <SummaryTile label="主目标" value={goalTitle || "-"} />
            </div>
          </div>

          <div className="rounded-3xl border border-cyan-100 bg-cyan-50/60 p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-cyan-950">将写入系统的研究 brief</h2>
            <p className="mt-2 text-sm leading-6 text-cyan-900/80">
              这份内容会进入任务上下文，并供后续多个 Agent 参考。
            </p>
            <div className="mt-4 rounded-2xl border border-cyan-100 bg-white px-4 py-4 text-sm leading-6 text-gray-700 whitespace-pre-wrap">
              {briefPreview || "你填写的结构化信息会在这里自动整理成一份简明的研究 brief。"}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function SummaryTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-gray-50 px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-gray-500">{label}</div>
      <div className="mt-1 text-base font-semibold text-gray-900">{value}</div>
    </div>
  );
}
