import { Link } from "react-router-dom";
import { BarChart3, Search, FileText, ShieldCheck } from "lucide-react";

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

export default function Landing() {
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
        <div className="mt-8">
          <Link
            to="/tasks/new"
            className="inline-flex items-center px-6 py-3 text-base font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
          >
            开始分析
          </Link>
        </div>
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
    </div>
  );
}
