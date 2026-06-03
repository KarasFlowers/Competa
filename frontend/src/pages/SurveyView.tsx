import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { surveyApi, type SurveyData, type SurveyQuestion } from "../api/client";
import { ArrowLeft, ClipboardCopy, Clock, Users } from "lucide-react";
import { useToast } from "../components/Toast";

const TYPE_LABELS: Record<string, string> = {
  single_choice: "单选",
  multiple_choice: "多选",
  likert_scale: "Likert量表",
  open_ended: "开放题",
  ranking: "排序题",
};

const TYPE_COLORS: Record<string, string> = {
  single_choice: "bg-blue-100 text-blue-700",
  multiple_choice: "bg-purple-100 text-purple-700",
  likert_scale: "bg-green-100 text-green-700",
  open_ended: "bg-amber-100 text-amber-700",
  ranking: "bg-pink-100 text-pink-700",
};

function QuestionCard({ q, index }: { q: SurveyQuestion; index: number }) {
  return (
    <div className="bg-white rounded-xl border p-5 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-mono text-gray-400">{q.id}</span>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TYPE_COLORS[q.type] || "bg-gray-100 text-gray-600"}`}>
          {TYPE_LABELS[q.type] || q.type}
        </span>
      </div>
      <p className="text-gray-900 font-medium">
        <span className="text-gray-400 mr-2">{index}.</span>
        {q.text}
      </p>
      {q.options.length > 0 && (
        <ul className="ml-6 space-y-1">
          {q.options.map((opt, i) => (
            <li key={i} className="text-sm text-gray-600 flex items-center gap-2">
              <span className="w-5 h-5 rounded-full border border-gray-300 flex items-center justify-center text-[10px] text-gray-400">
                {String.fromCharCode(65 + i)}
              </span>
              {opt}
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-3 text-xs text-gray-400">
        {q.target_persona && <span>👥 {q.target_persona}</span>}
        {q.dimension && <span>📊 {q.dimension}</span>}
      </div>
    </div>
  );
}

export default function SurveyView() {
  const { id } = useParams<{ id: string }>();
  const [survey, setSurvey] = useState<SurveyData | null>(null);
  const [error, setError] = useState("");
  const { toast } = useToast();

  useEffect(() => {
    if (!id) return;
    surveyApi.get(id).then((r) => setSurvey(r.data)).catch(() => setError("问卷数据未找到"));
  }, [id]);

  const handleCopy = () => {
    if (!survey) return;
    const text = survey.questions.map((q, i) => {
      let line = `${i}. [${TYPE_LABELS[q.type] || q.type}] ${q.text}`;
      if (q.options.length) line += "\n" + q.options.map((o, j) => `   ${String.fromCharCode(65 + j)}. ${o}`).join("\n");
      return line;
    }).join("\n\n");
    navigator.clipboard.writeText(`# ${survey.title}\n\n${survey.description}\n\n${text}`);
    toast("问卷已复制到剪贴板", "success");
  };

  if (error) return <div className="p-8 text-red-600">{error}</div>;
  if (!survey) return <div className="p-8 text-gray-500">Loading...</div>;

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <Link to={`/tasks/${id}`} className="text-blue-600 hover:underline text-sm flex items-center gap-1">
        <ArrowLeft className="w-4 h-4" /> 返回任务
      </Link>

      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl p-6 text-white">
        <h1 className="text-2xl font-bold">{survey.title || "竞品分析问卷"}</h1>
        {survey.description && <p className="mt-2 text-blue-100">{survey.description}</p>}
        <div className="flex gap-4 mt-4 text-sm text-blue-200">
          <span className="flex items-center gap-1"><Clock className="w-4 h-4" /> 约{survey.estimated_duration_min || 10}分钟</span>
          <span className="flex items-center gap-1"><Users className="w-4 h-4" /> {survey.target_audience || "目标用户"}</span>
          <span>{survey.questions.length} 题</span>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <ClipboardCopy className="w-4 h-4" /> 复制问卷
        </button>
      </div>

      <div className="space-y-4">
        {survey.questions.map((q, i) => (
          <QuestionCard key={q.id || i} q={q} index={i + 1} />
        ))}
      </div>
    </div>
  );
}
