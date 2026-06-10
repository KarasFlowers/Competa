import { Suspense, lazy, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { traceApi, Trace } from "../api/client";
import { ArrowLeft, Clock, Activity, SearchCode, ChevronDown, ChevronRight } from "lucide-react";

const LazyDagView = lazy(() => import("../components/DagView"));

function SectionLoading({ label }: { label: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-8 text-center text-sm text-gray-500">
      {label}
    </div>
  );
}

export default function TraceView() {
  const { id } = useParams<{ id: string }>();
  const [trace, setTrace] = useState<Trace | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!id) return;
    const fetchTrace = async () => {
      try {
        const { data } = await traceApi.list(id);
        if (data.length > 0) {
          // Find the pipeline trace
          const pipelineTrace = data.find((t) => t.agent_name === "pipeline") || data[0];
          setTrace(pipelineTrace);
        }
      } catch (err) {
        console.error("Failed to load traces", err);
      } finally {
        setLoading(false);
      }
    };
    fetchTrace();
  }, [id]);

  const toggleExpand = (eventId: string) => {
    setExpandedEvents((prev) => {
      const next = new Set(prev);
      if (next.has(eventId)) {
        next.delete(eventId);
      } else {
        next.add(eventId);
      }
      return next;
    });
  };

  if (loading) {
    return <div className="py-12 text-center text-gray-500">加载执行日志中...</div>;
  }

  if (!trace || !trace.events) {
    return (
      <div className="py-12 text-center text-gray-500">
        暂无执行追踪记录。<br />
        <Link to={`/tasks/${id}`} className="text-blue-600 hover:underline mt-2 inline-block">返回任务详情</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to={`/tasks/${id}`} className="p-2 text-gray-400 hover:text-gray-900 bg-white rounded-lg border shadow-sm">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">执行追踪与决策回放</h1>
            <p className="text-sm text-gray-500">查看多 Agent 协作流转与每步细节</p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm bg-white px-4 py-2 rounded-lg border shadow-sm">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-gray-400" />
            <span className="font-medium">{trace.total_duration ? `${trace.total_duration.toFixed(1)}s` : '-'}</span>
          </div>
          <div className="w-px h-4 bg-gray-200"></div>
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-gray-400" />
            <span className="font-medium">{trace.total_tokens || 0} tokens</span>
          </div>
        </div>
      </div>

      {/* DAG Visualization */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">执行链路图 (DAG)</h3>
        {id && (
          <Suspense fallback={<SectionLoading label="正在加载执行链路图..." />}>
            <LazyDagView taskId={id} height="280px" onNodeClick={(nodeId) => {
              // Scroll to and expand the first event for this agent in the timeline
              const eventIdx = trace?.events.findIndex((e) => e.agent_name === nodeId);
              if (eventIdx !== undefined && eventIdx >= 0) {
                const eventId = trace.events[eventIdx].id || `event-${eventIdx}`;
                setExpandedEvents((prev) => new Set(prev).add(eventId));
              }
            }} />
          </Suspense>
        )}
      </div>

      {/* Timeline */}
      <div className="bg-white rounded-xl shadow-sm border">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">执行时间线</h2>
        </div>
        <div className="p-6">
          <div className="relative border-l-2 border-gray-100 ml-4 space-y-8">
            {trace.events.map((event, index) => {
              const eventId = event.id || `event-${index}`;
              const isExpanded = expandedEvents.has(eventId);
              const isError = event.event_type === "error";
              
              let iconBg = "bg-gray-100 text-gray-500";
              if (isError) iconBg = "bg-red-100 text-red-600";
              else if (event.event_type === "start") iconBg = "bg-blue-100 text-blue-600";
              else if (event.event_type === "output") iconBg = "bg-green-100 text-green-600";

              return (
                <div key={eventId} className="relative pl-6">
                  {/* Timeline Dot */}
                  <div className={`absolute -left-3 top-1 w-6 h-6 rounded-full border-4 border-white flex items-center justify-center ${iconBg}`}>
                    <div className="w-2 h-2 rounded-full bg-current" />
                  </div>

                  <div className="bg-gray-50 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors">
                    {/* Event Header (Clickable) */}
                    <button 
                      onClick={() => toggleExpand(eventId)}
                      className="w-full text-left px-4 py-3 flex items-center justify-between focus:outline-none"
                    >
                      <div className="flex items-center gap-3">
                        <span className="px-2.5 py-0.5 rounded-md bg-white border shadow-sm text-xs font-semibold text-gray-700 uppercase tracking-wider">
                          {event.agent_name}
                        </span>
                        <span className="text-sm font-medium text-gray-900">
                          {event.event_type.toUpperCase()}
                        </span>
                        {(event.retry_attempt || 0) > 1 && (
                          <span className="text-xs text-amber-600 font-medium">
                            (Retry #{event.retry_attempt})
                          </span>
                        )}
                        <span className="text-sm text-gray-500">
                          {event.error_message || event.output_summary || event.input_summary}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-4 text-xs text-gray-400">
                        {event.duration && <span>{event.duration.toFixed(2)}s</span>}
                        {event.token_count && <span>{event.token_count} tkns</span>}
                        {event.timestamp && <span>{new Date(event.timestamp).toLocaleTimeString()}</span>}
                        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      </div>
                    </button>

                    {/* Event Details (Expanded) */}
                    {isExpanded && (
                      <div className="px-4 pb-4 pt-2 border-t border-gray-200 space-y-4">
                        {event.prompt && (
                          <div>
                            <h4 className="text-xs font-semibold text-gray-500 mb-1 flex items-center gap-1">
                              <SearchCode className="w-3 h-3" /> System + User Prompt
                            </h4>
                            <div className="bg-gray-900 text-gray-100 text-xs rounded-md p-3 whitespace-pre-wrap font-mono overflow-x-auto max-h-60 overflow-y-auto">
                              {event.prompt}
                            </div>
                          </div>
                        )}
                        {event.output_data && (
                          <div>
                            <h4 className="text-xs font-semibold text-gray-500 mb-1">Output Data / Schema</h4>
                            <div className="bg-white border rounded-md p-3 text-xs font-mono overflow-x-auto">
                              <pre>{JSON.stringify(event.output_data, null, 2)}</pre>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
