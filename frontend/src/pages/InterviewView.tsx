import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { interviewApi, type InterviewData, type InterviewQuestion } from "../api/client";
import { ArrowLeft, ClipboardCopy, Clock, Users, MessageCircle } from "lucide-react";
import { useToast } from "../components/Toast";

const PHASE_LABELS: Record<string, string> = {
  opening: "开场",
  core: "核心问题",
  probing: "深入追问",
  closing: "收尾",
};

const PHASE_COLORS: Record<string, string> = {
  opening: "bg-green-100 text-green-700 border-green-200",
  core: "bg-blue-100 text-blue-700 border-blue-200",
  probing: "bg-amber-100 text-amber-700 border-amber-200",
  closing: "bg-gray-100 text-gray-600 border-gray-200",
};

function InterviewQuestionCard({ q, index }: { q: InterviewQuestion; index: number }) {
  return (
    <div className={`rounded-xl border p-5 space-y-3 ${PHASE_COLORS[q.phase] || "bg-white border-gray-200"}`}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-mono opacity-60">{q.id}</span>
        <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-white/60">
          {PHASE_LABELS[q.phase] || q.phase}
        </span>
      </div>
      <p className="text-gray-900 font-medium">
        <span className="text-gray-400 mr-2">{index}.</span>
        {q.text}
      </p>
      {q.follow_ups.length > 0 && (
        <div className="ml-4 space-y-1.5">
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">追问策略</span>
          {q.follow_ups.map((fu, i) => (
            <div key={i} className="flex items-start gap-2 text-sm text-gray-600">
              <MessageCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 opacity-50" />
              <span>{fu}</span>
            </div>
          ))}
        </div>
      )}
      <div className="flex gap-3 text-xs opacity-60">
        {q.target_persona && <span>👥 {q.target_persona}</span>}
        {q.dimension && <span>📊 {q.dimension}</span>}
      </div>
    </div>
  );
}

export default function InterviewView() {
  const { id } = useParams<{ id: string }>();
  const [interview, setInterview] = useState<InterviewData | null>(null);
  const [error, setError] = useState("");
  const { toast } = useToast();

  useEffect(() => {
    if (!id) return;
    interviewApi.get(id).then((r) => setInterview(r.data)).catch(() => setError("访谈提纲未找到"));
  }, [id]);

  const handleCopy = () => {
    if (!interview) return;
    const text = interview.questions.map((q, i) => {
      let line = `${i}. [${PHASE_LABELS[q.phase] || q.phase}] ${q.text}`;
      if (q.follow_ups.length) line += "\n" + q.follow_ups.map((fu) => `   → ${fu}`).join("\n");
      return line;
    }).join("\n\n");
    const full = `# ${interview.title}\n\n开场白: ${interview.opening_script}\n\n${text}\n\n结束语: ${interview.closing_script}\n\n访谈提示: ${interview.notes}`;
    navigator.clipboard.writeText(full);
    toast("访谈提纲已复制到剪贴板", "success");
  };

  const phases = ["opening", "core", "probing", "closing"] as const;

  // Pre-compute question indices (must be before any early return — hook rules)
  const qIndexByPhase = useMemo(() => {
    const map = new Map<typeof phases[number], number[]>();
    if (!interview) return map;
    let idx = 0;
    for (const phase of phases) {
      const nums: number[] = [];
      for (const q of interview.questions) {
        if (q.phase === phase) {
          idx += 1;
          nums.push(idx);
        }
      }
      map.set(phase, nums);
    }
    return map;
  }, [interview, phases]);

  if (error) return <div className="p-8 text-red-600">{error}</div>;
  if (!interview) return <div className="p-8 text-gray-500">加载中...</div>;

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <Link to={`/tasks/${id}`} className="text-blue-600 hover:underline text-sm flex items-center gap-1">
        <ArrowLeft className="w-4 h-4" /> 返回任务
      </Link>

      <div className="bg-gradient-to-r from-emerald-600 to-teal-600 rounded-xl p-6 text-white">
        <h1 className="text-2xl font-bold">{interview.title || "用户访谈提纲"}</h1>
        <div className="flex gap-4 mt-4 text-sm text-emerald-200">
          <span className="flex items-center gap-1"><Clock className="w-4 h-4" /> 约{interview.estimated_duration_min || 30}分钟</span>
          <span className="flex items-center gap-1"><Users className="w-4 h-4" /> {interview.target_persona || "目标用户"}</span>
          <span>{interview.questions.length} 个问题</span>
        </div>
      </div>

      {/* Opening script */}
      {interview.opening_script && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-green-800 mb-2">🎤 开场白</h3>
          <p className="text-gray-700 leading-relaxed">{interview.opening_script}</p>
        </div>
      )}

      <div className="flex justify-end">
        <button
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <ClipboardCopy className="w-4 h-4" /> 复制提纲
        </button>
      </div>

      {/* Questions grouped by phase */}
      {phases.map((phase) => {
        const phaseQuestions = interview.questions.filter((q) => q.phase === phase);
        if (phaseQuestions.length === 0) return null;
        return (
          <div key={phase} className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {PHASE_LABELS[phase]}
            </h3>
            {phaseQuestions.map((q, qi) => {
              const idx = (qIndexByPhase.get(phase) ?? [])[qi] ?? 0;
              return <InterviewQuestionCard key={q.id || `${phase}-${qi}`} q={q} index={idx} />;
            })}
          </div>
        );
      })}

      {/* Closing script */}
      {interview.closing_script && (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-600 mb-2">👋 结束语</h3>
          <p className="text-gray-700 leading-relaxed">{interview.closing_script}</p>
        </div>
      )}

      {/* Interviewer notes */}
      {interview.notes && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-amber-800 mb-2">📝 访谈提示</h3>
          <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{interview.notes}</p>
        </div>
      )}
    </div>
  );
}
