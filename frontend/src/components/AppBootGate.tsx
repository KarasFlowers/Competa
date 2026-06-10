import { useEffect, useRef, useState, type ReactNode } from "react";
import { BarChart3, RefreshCw } from "lucide-react";

const RETRY_DELAYS_MS = [500, 900, 1400, 2000, 2600, 3200];
const TROUBLESHOOTING_THRESHOLD_MS = 12000;

type BootStatus = "checking" | "waiting" | "ready";

function resolveBootErrorMessage(error: unknown) {
  if (!(error instanceof Error)) {
    return "后端暂时还没有响应";
  }

  if (
    error.message.startsWith("HTTP ") ||
    error.message === "Health check did not return ok" ||
    error.message === "Failed to fetch"
  ) {
    return "后端暂时还没有响应";
  }

  return error.message;
}

export default function AppBootGate({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<BootStatus>("checking");
  const [failedAttempts, setFailedAttempts] = useState(0);
  const [lastError, setLastError] = useState("");
  const [showTroubleshooting, setShowTroubleshooting] = useState(false);
  const [probeSeed, setProbeSeed] = useState(0);
  const retryTimerRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    const startedAt = Date.now();

    const clearRetryTimer = () => {
      if (retryTimerRef.current !== null) {
        window.clearTimeout(retryTimerRef.current);
        retryTimerRef.current = null;
      }
    };

    const scheduleRetry = (attempt: number) => {
      const delay = RETRY_DELAYS_MS[Math.min(attempt, RETRY_DELAYS_MS.length - 1)];
      retryTimerRef.current = window.setTimeout(() => {
        void probe(attempt + 1);
      }, delay);
    };

    const probe = async (attempt: number) => {
      if (cancelled) {
        return;
      }

      setStatus(attempt === 0 ? "checking" : "waiting");

      try {
        const response = await fetch(`/api/health?boot=${Date.now()}`, {
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const payload = await response.json();
        if (payload.status !== "ok") {
          throw new Error("Health check did not return ok");
        }

        if (cancelled) {
          return;
        }

        clearRetryTimer();
        setStatus("ready");
        setFailedAttempts(0);
        setLastError("");
        setShowTroubleshooting(false);
      } catch (error) {
        if (cancelled) {
          return;
        }

        const elapsed = Date.now() - startedAt;
        setFailedAttempts(attempt + 1);
        setStatus("waiting");
        setLastError(resolveBootErrorMessage(error));
        setShowTroubleshooting(elapsed >= TROUBLESHOOTING_THRESHOLD_MS);
        scheduleRetry(attempt);
      }
    };

    void probe(0);

    return () => {
      cancelled = true;
      clearRetryTimer();
    };
  }, [probeSeed]);

  if (status === "ready") {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-blue-950 text-white">
      <div className="mx-auto flex min-h-screen max-w-5xl items-center px-6 py-12">
        <div className="grid w-full gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <section className="rounded-[32px] border border-white/10 bg-white/[0.08] p-8 shadow-2xl backdrop-blur">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-sm font-medium text-blue-100">
              <BarChart3 className="h-4 w-4" />
              Competa
            </div>
            <h1 className="mt-5 text-3xl font-semibold tracking-tight sm:text-4xl">
              正在等待后端服务启动完成
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-blue-100 sm:text-base">
              这通常发生在前端比后端先启动几秒的时候。我们会自动重试连接，避免把短暂的启动过程误显示成“无法连接”。
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-sm text-blue-50">
                <RefreshCw className={`h-4 w-4 ${status === "checking" ? "animate-spin" : ""}`} />
                {status === "checking" ? "正在检查后端健康状态" : "后端尚未就绪，正在自动重试"}
              </div>
              <div className="rounded-full bg-white/10 px-4 py-2 text-sm text-blue-100">
                已重试 {failedAttempts} 次
              </div>
            </div>

            <div className="mt-8 rounded-3xl border border-white/10 bg-slate-950/30 p-5 text-sm text-blue-100">
              <div className="font-medium text-white">这段等待时间里，系统通常在做两件事</div>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="font-medium text-white">应用初始化</div>
                  <p className="mt-2 leading-6 text-blue-100">
                    FastAPI 启动、装配路由，并准备数据库连接与基础服务。
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="font-medium text-white">前端自动探活</div>
                  <p className="mt-2 leading-6 text-blue-100">
                    浏览器会持续探测 `/api/health`，一旦后端就绪就自动进入应用。
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => {
                  setStatus("checking");
                  setFailedAttempts(0);
                  setLastError("");
                  setShowTroubleshooting(false);
                  setProbeSeed((value) => value + 1);
                }}
                className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-medium text-slate-900 transition-colors hover:bg-blue-50"
              >
                <RefreshCw className="h-4 w-4" />
                立即重试
              </button>
              {lastError ? (
                <span className="text-xs text-blue-200">
                  最近一次错误：{lastError}
                </span>
              ) : null}
            </div>
          </section>

          <aside className="space-y-4">
            <div className="rounded-[28px] border border-white/10 bg-white/[0.08] p-6 shadow-xl backdrop-blur">
              <h2 className="text-lg font-semibold text-white">为什么这样处理</h2>
              <div className="mt-3 space-y-3 text-sm leading-6 text-blue-100">
                <p>启动几秒内的连接失败并不代表系统真的不可用，更像是服务还在热身。</p>
                <p>把这种瞬时失败展示成红色报错，会让用户误以为项目本身有问题。</p>
                <p>现在应用会先等待后端就绪，再让各页面发起正式请求。</p>
              </div>
            </div>

            {showTroubleshooting ? (
              <div className="rounded-[28px] border border-amber-300/30 bg-amber-400/10 p-6 text-sm leading-6 text-amber-100">
                <div className="font-semibold text-white">等待时间偏长</div>
                <div className="mt-3 space-y-2">
                  <p>如果你刚刚同时启动前后端，这通常还是正常的。</p>
                  <p>如果持续很久都没有进入应用，再检查后端进程是否真的已经启动成功。</p>
                </div>
              </div>
            ) : null}
          </aside>
        </div>
      </div>
    </div>
  );
}
