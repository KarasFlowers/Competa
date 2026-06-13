import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { BarChart3, Search, FileText, ShieldCheck, Play, Pause, Eye, FolderKanban } from "lucide-react";
import { demoApi, type DemoScenarioSummary } from "../api/client";

const features = [
  {
    icon: Search,
    title: "智能采集",
    desc: "多源信息自动采集，覆盖公开网页、文档、问卷与访谈",
  },
  {
    icon: BarChart3,
    title: "结构化分析",
    desc: "功能树、定价模型、用户画像、SWOT 自动提取与对比",
  },
  {
    icon: FileText,
    title: "报告生成",
    desc: "结构化竞品分析报告，每条结论可溯源至原始数据",
  },
  {
    icon: ShieldCheck,
    title: "质检闭环",
    desc: "质检 Agent 自动校验并打回不合格内容，确保输出可信",
  },
];

// ---------------------------------------------------------------------------
// Agent Collaboration Simulator
// ---------------------------------------------------------------------------

interface SimStep {
  agent: string;
  color: string;
  desc: string;
  tokens: number;
  duration: string;
  sampleTitle: string;
  sampleContent: React.ReactNode;
}

// --- Sample output data per agent ---

function SourceSample() {
  return (
    <div className="space-y-2">
      {[
        { url: "https://www.doubao.com", title: "豆包官网", snippet: "多模态理解与生成，与抖音/飞书/即梦深度集成", type: "url" },
        { url: "https://kimi.moonshot.cn", title: "Kimi 官网", snippet: "200 万字超长上下文窗口，深度阅读与文档总结", type: "url" },
        { url: null, title: "36氪: AI 对话助手行业报告", snippet: "2025 年 AI 对话助手市场形成「一超多强」格局", type: "document" },
        { url: null, title: "用户满意度调研 N=1200", snippet: "豆包满意度 4.2/5，Kimi 4.0/5，DeepSeek 3.8/5", type: "survey" },
      ].map((s, i) => (
        <div key={i} className="flex items-start gap-2 text-sm">
          <span className="mt-0.5 shrink-0 rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-medium text-blue-700">{s.type}</span>
          <div className="min-w-0">
            <div className="font-medium text-gray-800 truncate">{s.title}</div>
            <div className="text-xs text-gray-500 line-clamp-1">{s.snippet}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

function SurveySample() {
  return (
    <div className="space-y-2 text-sm">
      {[
        { q: "您目前主要使用哪款 AI 助手？", type: "单选", options: ["豆包", "Kimi", "DeepSeek", "通义千问", "其他"] },
        { q: "您使用 AI 助手的频率？", type: "单选", options: ["每天多次", "每天一次", "每周几次", "偶尔使用"] },
        { q: "请评价主要使用产品的响应速度", type: "Likert", options: ["非常不满意", "不满意", "一般", "满意", "非常满意"] },
      ].map((s, i) => (
        <div key={i} className="rounded-lg bg-gray-50 p-2.5">
          <div className="font-medium text-gray-800">{i + 1}. {s.q}</div>
          <div className="mt-1.5 flex flex-wrap gap-1">
            {s.options.map((o, j) => (
              <span key={j} className="rounded-full border border-gray-200 bg-white px-2 py-0.5 text-xs text-gray-500">{o}</span>
            ))}
          </div>
          <div className="mt-1 text-[11px] text-gray-400">{s.type}题</div>
        </div>
      ))}
    </div>
  );
}

function InterviewSample() {
  return (
    <div className="space-y-2 text-sm">
      {[
        { q: "请简单介绍一下您的日常工作流程，以及协同办公工具在其中的角色。", phase: "开场", persona: "团队管理者" },
        { q: "在使用当前工具的过程中，有没有遇到过让您特别头疼的场景？能举一个具体的例子吗？", phase: "核心", persona: "团队管理者" },
        { q: "如果让您给当前工具的产品经理提三个改进建议，您会说什么？", phase: "深入追问", persona: "重度用户" },
      ].map((s, i) => (
        <div key={i} className="rounded-lg bg-gray-50 p-2.5">
          <div className="flex items-center gap-2">
            <span className="shrink-0 rounded bg-teal-100 px-1.5 py-0.5 text-[10px] font-medium text-teal-700">{s.phase}</span>
            <span className="text-[11px] text-gray-400">{s.persona}</span>
          </div>
          <div className="mt-1 font-medium text-gray-800">{i + 1}. {s.q}</div>
        </div>
      ))}
    </div>
  );
}

function FieldworkSample() {
  return (
    <div className="space-y-2 text-sm">
      {[
        { persona: "企业决策者 (N≈80)", finding: "72% 认为价格透明度和API稳定性是选型首要因素；56% 关注数据安全合规" },
        { persona: "个体开发者 (N≈150)", finding: "多数受访者因免费额度选择了豆包或DeepSeek，但深度使用后开始关注模型能力差异" },
        { persona: "产品经理 · 访谈摘录", quote: "我们评估了三家，最后选了豆包主要因为飞书集成太方便了——团队不用再开一个新工具。", insight: "生态集成是豆包的核心护城河" },
      ].map((s, i) => (
        <div key={i} className="rounded-lg bg-gray-50 p-2.5">
          <div className="text-[11px] font-medium text-emerald-700">{s.persona}</div>
          {s.finding && <div className="mt-0.5 text-gray-700">{s.finding}</div>}
          {s.quote && <div className="mt-1 text-gray-600 italic">"{s.quote}"</div>}
          {s.insight && <div className="mt-0.5 text-[11px] text-emerald-600">← {s.insight}</div>}
        </div>
      ))}
    </div>
  );
}

function AnalystSample() {
  return (
    <div className="space-y-2 text-sm">
      <div className="rounded-lg bg-gray-50 p-3">
        <div className="text-[11px] font-medium text-purple-700 uppercase tracking-wider">功能对比矩阵</div>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-1 pr-2 text-gray-400 font-medium">维度</th>
                <th className="text-left py-1 px-2">豆包</th>
                <th className="text-left py-1 px-2">Kimi</th>
                <th className="text-left py-1 px-2">DeepSeek</th>
              </tr>
            </thead>
            <tbody className="text-gray-700">
              <tr className="border-b border-gray-100"><td className="py-1 pr-2 text-gray-500">上下文窗口</td><td className="py-1 px-2">128K</td><td className="py-1 px-2 font-medium">200万字 ★</td><td className="py-1 px-2">128K</td></tr>
              <tr className="border-b border-gray-100"><td className="py-1 pr-2 text-gray-500">多模态</td><td className="py-1 px-2 font-medium">文/图/音/视频 ★</td><td className="py-1 px-2">文本+图</td><td className="py-1 px-2">文本+图+代码</td></tr>
              <tr><td className="py-1 pr-2 text-gray-500">API 定价</td><td className="py-1 px-2">中等</td><td className="py-1 px-2">中高</td><td className="py-1 px-2 font-medium text-green-600">极低 ★</td></tr>
            </tbody>
          </table>
        </div>
      </div>
      <div className="rounded-lg bg-gray-50 p-3">
        <div className="text-[11px] font-medium text-purple-700 uppercase tracking-wider">SWOT · 豆包</div>
        <div className="mt-1.5 grid grid-cols-2 gap-2 text-xs">
          <div className="rounded bg-green-50 px-2 py-1"><span className="font-medium text-green-700">S</span><span className="text-gray-600"> 抖音/飞书/即梦超级矩阵导流</span></div>
          <div className="rounded bg-red-50 px-2 py-1"><span className="font-medium text-red-700">W</span><span className="text-gray-600"> 深度推理弱于 DeepSeek R1</span></div>
          <div className="rounded bg-blue-50 px-2 py-1"><span className="font-medium text-blue-700">O</span><span className="text-gray-600"> AI 搜索替代传统搜索</span></div>
          <div className="rounded bg-amber-50 px-2 py-1"><span className="font-medium text-amber-700">T</span><span className="text-gray-600"> DeepSeek 开源侵蚀 API 市场</span></div>
        </div>
      </div>
    </div>
  );
}

function WriterSample() {
  return (
    <div className="space-y-2 text-sm">
      <div className="rounded-lg bg-gray-50 p-3">
        <div className="font-semibold text-gray-900">市场格局概览</div>
        <div className="mt-1 text-gray-600 leading-relaxed text-xs">
          中国 AI 对话助手市场在 2024-2025 年经历了爆发式增长，形成了「一超多强」的竞争格局。字节跳动的豆包凭借抖音、飞书等超级应用的导流效应，以超过 2 亿月活的规模遥遥领先。
        </div>
        <div className="mt-2 flex flex-wrap gap-1">
          <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] text-blue-700">豆包月活 2.27 亿 · 置信度 0.95</span>
          <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] text-blue-700">市场一超多强 · 置信度 0.90</span>
        </div>
      </div>
      <div className="rounded-lg bg-gray-50 p-3">
        <div className="font-semibold text-gray-900">战略建议</div>
        <div className="mt-1 text-xs text-gray-600 space-y-1">
          <div>1. 豆包应强化深度推理能力，补齐与 DeepSeek R1 的差距</div>
          <div>2. 关注 AI 搜索替代传统搜索趋势，依托字节搜索能力抢占入口</div>
          <div>3. 智能体生态是下一个增长点，形成类似 App Store 的生态效应</div>
        </div>
      </div>
    </div>
  );
}

function FilterSample() {
  return (
    <div className="text-sm">
      <div className="rounded-lg bg-gray-50 p-3 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-500">总声明数</span><span className="font-medium">15</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-500">有证据支撑</span><span className="font-medium text-green-600">15</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-500">无证据剔除</span><span className="font-medium text-amber-600">0</span>
        </div>
        <div className="mt-1 pt-2 border-t border-gray-200 text-xs text-gray-400">
          所有声明均有至少一条来源支撑，无需过滤。
        </div>
      </div>
    </div>
  );
}

function QASample() {
  return (
    <div className="text-sm space-y-2">
      <div className="rounded-lg bg-gray-50 p-3">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">✓ QA 通过</span>
        </div>
        <div className="mt-2 space-y-1.5 text-xs text-gray-600">
          <div className="flex justify-between"><span>证据覆盖率</span><span className="font-medium text-green-600">93%</span></div>
          <div className="flex justify-between"><span>来源数量</span><span className="font-medium">8</span></div>
          <div className="flex justify-between"><span>有证据声明数</span><span className="font-medium">15 / 15</span></div>
        </div>
      </div>
      <div className="text-xs text-gray-400">所有检查项通过，报告质量合格。</div>
    </div>
  );
}

const SIM_STEPS: SimStep[] = [
  { agent: "Collector", color: "bg-blue-500", desc: "搜索并采集竞品公开信息", tokens: 2350, duration: "3.1s", sampleTitle: "采集到的来源", sampleContent: <SourceSample /> },
  { agent: "Survey", color: "bg-cyan-500", desc: "设计竞品分析问卷", tokens: 1800, duration: "2.2s", sampleTitle: "问卷题目示例", sampleContent: <SurveySample /> },
  { agent: "Interview", color: "bg-teal-500", desc: "设计半结构化用户访谈提纲", tokens: 1500, duration: "1.8s", sampleTitle: "访谈提纲示例", sampleContent: <InterviewSample /> },
  { agent: "Fieldwork", color: "bg-emerald-500", desc: "模拟执行问卷与访谈，回流为可溯源证据", tokens: 2100, duration: "2.5s", sampleTitle: "调研执行结果", sampleContent: <FieldworkSample /> },
  { agent: "Analyst", color: "bg-purple-500", desc: "提取功能对比、定价、SWOT 结构化洞察", tokens: 3180, duration: "2.8s", sampleTitle: "结构化分析产物", sampleContent: <AnalystSample /> },
  { agent: "Writer", color: "bg-green-500", desc: "生成含引用的结构化竞品分析报告", tokens: 4560, duration: "4.2s", sampleTitle: "报告章节预览", sampleContent: <WriterSample /> },
  { agent: "Filter", color: "bg-yellow-500", desc: "过滤无证据支撑的声明", tokens: 120, duration: "0.3s", sampleTitle: "证据过滤统计", sampleContent: <FilterSample /> },
  { agent: "QA", color: "bg-red-500", desc: "校验报告完整性、证据覆盖率", tokens: 1890, duration: "1.8s", sampleTitle: "质检结果", sampleContent: <QASample /> },
];

function AgentSimulator() {
  const [currentStep, setCurrentStep] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(true);
  const [isDone, setIsDone] = useState(false);
  // null = follow animation automatically; a number = user manually pinned a step
  const [pinnedIdx, setPinnedIdx] = useState<number | null>(null);

  const reset = useCallback(() => {
    setCurrentStep(-1);
    setIsPlaying(true);
    setIsDone(false);
    setPinnedIdx(null);
  }, []);

  // Auto-advance: slower pace (3s) so the expanded detail is readable
  useEffect(() => {
    if (!isPlaying) return;
    if (currentStep < 0) { setCurrentStep(0); return; }
    if (currentStep >= SIM_STEPS.length - 1) { setIsPlaying(false); setIsDone(true); return; }
    const timer = setTimeout(() => setCurrentStep((prev) => prev + 1), 3000);
    return () => clearTimeout(timer);
  }, [isPlaying, currentStep]);

  // Auto-restart after cycle completes
  useEffect(() => {
    if (!isDone) return;
    const timer = setTimeout(reset, 3000);
    return () => clearTimeout(timer);
  }, [isDone, reset]);

  // When not paused, expanded follows the current step.  When paused, the
  // user can click any completed step to pin it (and pause the animation so
  // they can read at their own pace).
  const expandedIdx = pinnedIdx ?? (currentStep >= 0 ? currentStep : null);

  const handleToggle = () => {
    if (isDone) { reset(); return; }
    if (isPlaying) {
      // Pausing: pin to current step so details stay visible.
      setIsPlaying(false);
      if (currentStep >= 0) setPinnedIdx(currentStep);
    } else {
      // Resuming: release pin and continue animation.
      setPinnedIdx(null);
      setIsPlaying(true);
    }
  };

  const handleStepClick = (i: number) => {
    if (i > currentStep) return; // not yet reached — can't preview
    if (pinnedIdx === i) {
      // Unpin: resume animation from current step
      setPinnedIdx(null);
      setIsPlaying(true);
    } else {
      // Pin to this step and pause animation
      setPinnedIdx(i);
      setIsPlaying(false);
    }
  };

  const totalTokens = SIM_STEPS.slice(0, currentStep + 1).reduce((s, step) => s + step.tokens, 0);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Agent 协作模拟器</h3>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-gray-400 hidden sm:inline">自动演示中 · 点击步骤可暂停查看</span>
          <button
            onClick={handleToggle}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
          >
            {isPlaying ? <><Pause className="w-4 h-4" /> 暂停</> :
             <><Play className="w-4 h-4" /> 播放</>}
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all duration-700"
          style={{ width: `${((currentStep + 1) / SIM_STEPS.length) * 100}%` }}
        />
      </div>

      {/* Agent steps */}
      <div className="space-y-2">
        {SIM_STEPS.map((step, i) => {
          const isActive = i === currentStep && isPlaying;
          const isCompleted = i <= currentStep;
          const isExpanded = expandedIdx === i;
          return (
            <div key={i}>
              <button
                onClick={() => handleStepClick(i)}
                className={`w-full flex items-center gap-4 p-3 rounded-lg transition-all duration-500 text-left ${
                  isActive ? "bg-blue-50 border border-blue-200 scale-[1.02]" :
                  isCompleted ? "bg-gray-50 border border-gray-200" :
                  "opacity-40 bg-white border border-gray-100"
                } ${isExpanded ? "shadow-sm rounded-b-none" : ""}`}
              >
                <div className={`w-10 h-10 rounded-full ${step.color} flex items-center justify-center text-white text-sm font-bold flex-shrink-0 transition-shadow ${
                  isActive ? "ring-2 ring-offset-2 ring-blue-400 animate-pulse" : ""
                }`}>
                  {step.agent.slice(0, 2).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-gray-900">{step.agent}</div>
                  <div className="text-sm text-gray-500">{step.desc}</div>
                </div>
                {isCompleted && (
                  <div className="text-xs text-gray-400 flex-shrink-0 text-right">
                    <div>{step.tokens.toLocaleString()} Tokens</div>
                    <div>{step.duration}</div>
                  </div>
                )}
                <svg className={`w-4 h-4 text-gray-300 flex-shrink-0 transition-transform duration-300 ${isExpanded ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>
              </button>

              {/* Expanded sample content — full width, smooth height animation */}
              <div
                className="overflow-hidden transition-all duration-500 ease-in-out"
                style={{
                  maxHeight: isExpanded ? "24rem" : "0",
                  opacity: isExpanded ? 1 : 0,
                }}
              >
                <div className="rounded-b-xl border border-t-0 border-gray-100 bg-gradient-to-br from-gray-50 to-white p-4 shadow-inner">
                  <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">{step.sampleTitle}</div>
                  {step.sampleContent}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Stats */}
      {currentStep >= 0 && (
        <div className="flex items-center gap-6 pt-3 border-t border-gray-100 text-sm text-gray-600">
          <span>累计 Tokens：<strong>{totalTokens.toLocaleString()}</strong></span>
          <span>流程耗时：<strong>{SIM_STEPS.slice(0, currentStep + 1).reduce((s, step) => s + parseFloat(step.duration), 0).toFixed(1)}s</strong></span>
          <span>已完成步骤：<strong>{currentStep + 1}/{SIM_STEPS.length}</strong></span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Landing Page
// ---------------------------------------------------------------------------
export default function Landing() {
  const [demos, setDemos] = useState<DemoScenarioSummary[]>([]);

  useEffect(() => {
    demoApi.list().then((r) => setDemos(r.data)).catch(() => {
      console.warn("Demo scenarios failed to load — they will not be shown on this page.");
    });
  }, []);

  return (
    <div className="space-y-16">
      {/* Hero */}
      <section className="text-center pt-12">
        <h1 className="text-4xl font-bold text-gray-900 sm:text-5xl">
          AI 驱动的竞品分析
        </h1>
        <p className="mt-4 text-lg text-gray-600 max-w-2xl mx-auto">
          多 Agent 协作的数字调研小组，从信息采集到结构化报告，全链路自动化。
        </p>
        <div className="mt-8 flex items-center justify-center gap-4">
          <Link
            to="/tasks/new"
            className="inline-flex items-center px-6 py-3 text-base font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
          >
            开始分析
          </Link>
          <Link
            to="/tasks"
            className="inline-flex items-center px-6 py-3 text-base font-medium text-blue-700 bg-white border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors"
          >
            <FolderKanban className="w-5 h-5 mr-2" /> 任务工作台
          </Link>
        </div>
        {demos.length > 0 && (
          <div className="mt-4">
            <a
              href="#demos"
              className="inline-flex items-center text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              <Eye className="w-4 h-4 mr-1.5" /> 查看示例场景
            </a>
          </div>
        )}
      </section>

      {/* Agent Simulator */}
      <section>
        <AgentSimulator />
      </section>

      {/* Features */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {features.map((f) => (
          <div
            key={f.title}
            className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
          >
            <f.icon className="w-8 h-8 text-blue-600 mb-4" />
            <h3 className="text-lg font-semibold text-gray-900">{f.title}</h3>
            <p className="mt-2 text-sm text-gray-600">{f.desc}</p>
          </div>
        ))}
      </section>

      {/* Demo Scenarios */}
      {demos.length > 0 && (
        <section id="demos">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900">即刻体验</h2>
            <p className="mt-2 text-gray-600">预置场景，秒级查看完整竞品分析报告</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {demos.map((demo) => {
              const colorMap: Record<string, string> = {
                "AI 对话助手": "from-blue-500 to-indigo-600",
                "短视频/社交媒体": "from-pink-500 to-rose-600",
                "AI 开发工具": "from-emerald-500 to-teal-600",
              };
              const gradient = colorMap[demo.industry] || "from-gray-500 to-gray-700";
              return (
                <Link
                  key={demo.id}
                  to={`/demos/${demo.id}`}
                  className="group bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg transition-all"
                >
                  <div className={`bg-gradient-to-r ${gradient} p-5 text-white`}>
                    <h3 className="font-bold text-lg">{demo.name}</h3>
                    <p className="text-sm opacity-90 mt-1">{demo.industry}</p>
                  </div>
                  <div className="p-5 space-y-3">
                    <p className="text-sm text-gray-600">{demo.description}</p>
                    <div className="flex flex-wrap gap-1">
                      {demo.competitors.slice(0, 3).map((c) => (
                        <span key={c.name} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                          {c.name}
                        </span>
                      ))}
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {demo.focus_areas.slice(0, 3).map((fa) => (
                        <span key={fa} className="px-2 py-0.5 bg-blue-50 text-blue-600 text-xs rounded">
                          {fa}
                        </span>
                      ))}
                    </div>
                    <div className="pt-2 text-blue-600 text-sm font-medium flex items-center group-hover:underline">
                      查看完整报告 <span className="inline-block transition-transform group-hover:translate-x-1 ml-1">→</span>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
