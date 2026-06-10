import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { BarChart3, Search, FileText, ShieldCheck, Play, Pause, RotateCcw, Eye, FolderKanban } from "lucide-react";
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
const SIM_STEPS = [
  { agent: "Collector", color: "bg-blue-500", desc: "搜索并采集竞品公开信息", tokens: 2350, duration: "3.1s" },
  { agent: "Survey", color: "bg-cyan-500", desc: "设计竞品分析问卷", tokens: 1800, duration: "2.2s" },
  { agent: "Interview", color: "bg-teal-500", desc: "设计半结构化用户访谈提纲", tokens: 1500, duration: "1.8s" },
  { agent: "Fieldwork", color: "bg-emerald-500", desc: "模拟执行问卷与访谈，回流为可溯源证据", tokens: 2100, duration: "2.5s" },
  { agent: "Analyst", color: "bg-purple-500", desc: "提取功能对比、定价、SWOT 结构化洞察", tokens: 3180, duration: "2.8s" },
  { agent: "Writer", color: "bg-green-500", desc: "生成含引用的结构化竞品分析报告", tokens: 4560, duration: "4.2s" },
  { agent: "Filter", color: "bg-yellow-500", desc: "过滤无证据支撑的声明", tokens: 120, duration: "0.3s" },
  { agent: "QA", color: "bg-red-500", desc: "校验报告完整性、证据覆盖率", tokens: 1890, duration: "1.8s" },
];

function AgentSimulator() {
  const [currentStep, setCurrentStep] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isDone, setIsDone] = useState(false);

  const reset = useCallback(() => {
    setCurrentStep(-1);
    setIsPlaying(false);
    setIsDone(false);
  }, []);

  useEffect(() => {
    if (!isPlaying) return;
    // First step should appear immediately
    if (currentStep < 0) {
      setCurrentStep(0);
      return;
    }
    if (currentStep >= SIM_STEPS.length - 1) {
      setIsPlaying(false);
      setIsDone(true);
      return;
    }
    const timer = setTimeout(() => {
      setCurrentStep((prev) => prev + 1);
    }, 1200);
    return () => clearTimeout(timer);
  }, [isPlaying, currentStep]);

  const totalTokens = SIM_STEPS.slice(0, currentStep + 1).reduce((s, step) => s + step.tokens, 0);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Agent 协作模拟器</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { if (isDone) reset(); setIsPlaying(!isPlaying); }}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
          >
            {isDone ? <><RotateCcw className="w-4 h-4" /> 重播</> :
             isPlaying ? <><Pause className="w-4 h-4" /> 暂停</> :
             <><Play className="w-4 h-4" /> 播放</>}
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all duration-500"
          style={{ width: `${((currentStep + 1) / SIM_STEPS.length) * 100}%` }}
        />
      </div>

      {/* Agent steps */}
      <div className="space-y-3">
        {SIM_STEPS.map((step, i) => {
          const isActive = i === currentStep && isPlaying;
          const isCompleted = i <= currentStep;
          return (
            <div
              key={i}
              className={`flex items-center gap-4 p-3 rounded-lg transition-all duration-300 ${
                isActive ? "bg-blue-50 border border-blue-200 scale-[1.02]" :
                isCompleted ? "bg-gray-50 border border-gray-200" :
                "opacity-40"
              }`}
            >
              <div className={`w-10 h-10 rounded-full ${step.color} flex items-center justify-center text-white text-sm font-bold flex-shrink-0 ${
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
    demoApi.list().then((r) => setDemos(r.data)).catch(() => {});
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
