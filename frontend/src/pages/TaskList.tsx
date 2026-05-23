import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Clock, BarChart3 } from "lucide-react";
import { taskApi, type Task } from "../api/client";

const statusLabel: Record<string, { text: string; cls: string }> = {
  pending: { text: "待执行", cls: "bg-gray-100 text-gray-700" },
  running: { text: "执行中", cls: "bg-blue-100 text-blue-700" },
  completed: { text: "已完成", cls: "bg-green-100 text-green-700" },
  failed: { text: "失败", cls: "bg-red-100 text-red-700" },
};

function formatTime(iso: string) {
  return new Date(iso).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function TaskList() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    taskApi
      .list()
      .then((r) => setTasks(r.data))
      .catch(() => setTasks([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-gray-400">
        加载中…
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="text-center py-20">
        <BarChart3 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <h2 className="text-lg font-medium text-gray-600 mb-2">暂无分析任务</h2>
        <p className="text-sm text-gray-400 mb-6">创建第一个竞品分析任务</p>
        <Link
          to="/tasks/new"
          className="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" /> 新建分析
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">分析任务</h1>
        <Link
          to="/tasks/new"
          className="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" /> 新建分析
        </Link>
      </div>

      <div className="space-y-3">
        {tasks.map((task) => {
          const st = statusLabel[task.status] ?? {
            text: task.status,
            cls: "bg-gray-100 text-gray-700",
          };
          return (
            <Link
              key={task.id}
              to={`/tasks/${task.id}`}
              className="block bg-white rounded-xl p-5 shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h3 className="text-base font-semibold text-gray-900 truncate">
                    {task.target_product}
                  </h3>
                  <div className="mt-1 flex items-center gap-3 text-sm text-gray-500">
                    {task.industry && <span>{task.industry}</span>}
                    {task.competitors.length > 0 && (
                      <span>竞品: {task.competitors.join("、")}</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3 ml-4">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${st.cls}`}
                  >
                    {st.text}
                  </span>
                  <span className="flex items-center gap-1 text-xs text-gray-400">
                    <Clock className="w-3 h-3" />
                    {formatTime(task.created_at)}
                  </span>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
