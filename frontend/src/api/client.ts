import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

export function externalHref(url: string | null | undefined) {
  const trimmed = url?.trim() ?? "";
  if (!trimmed) return "";
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed.replace(/^\/+/, "")}`;
}

export function formatWebsiteLabel(url: string) {
  return url.replace(/^https?:\/\//i, "").replace(/\/$/, "");
}

export interface CompetitorInput {
  name: string;
  category: string;  // direct | indirect | substitute
  website?: string | null;
  notes?: string;
  tags?: string[];
}

export interface CurationSummary {
  input_count?: number;
  kept_count?: number;
  removed_count?: number;
  first_party_count?: number;
  avg_reliability?: number | null;
  removed_reasons?: Record<string, number>;
}

export interface Task {
  id: string;
  industry: string;
  target_product: string;
  target_website: string;
  competitors: (string | CompetitorInput)[];
  focus_areas: string[];
  our_product_notes: string;
  output_language: string;  // "zh" | "en"
  human_review_required: boolean;
  manual_correction_count: number;
  last_qa_feedback: Record<string, unknown>;
  last_handoff: Record<string, unknown>;
  last_curation_summary: CurationSummary;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface TaskArtifactSummary {
  report: boolean;
  analysis: boolean;
  traces: boolean;
  survey: boolean;
  interview: boolean;
}

export interface TaskMetricsSummary {
  source_count: number;
  claim_count: number;
  evidence_coverage_rate: number;
  quality_score: number;
  quality_breakdown: Record<string, unknown>;
  manual_correction_count: number;
}

export interface TaskOverviewItem extends Task {
  metrics: TaskMetricsSummary | null;
  artifacts: TaskArtifactSummary;
}

export interface TaskOverviewStats {
  total_tasks: number;
  active_tasks: number;
  review_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  reports_ready: number;
  avg_evidence_coverage: number | null;
  avg_quality_score: number | null;
  status_counts: Record<string, number>;
}

export interface TaskOverviewResponse {
  stats: TaskOverviewStats;
  items: TaskOverviewItem[];
}

export interface TaskCreatePayload {
  industry?: string;
  target_product: string;
  target_website?: string;
  competitors?: (string | CompetitorInput)[];
  focus_areas?: string[];
  our_product_notes?: string;
  output_language?: "zh" | "en";
  human_review_required?: boolean;
}

export interface Report {
  id: string;
  task_id: string;
  title: string;
  content: ReportContent;
  status: string;
  created_at: string;
}

export type ReportExportFormat = "markdown" | "docx";

export interface ReportContent {
  title?: string;
  executive_summary?: string;
  sections?: ReportSection[];
  [key: string]: unknown;
}

export interface ReportSection {
  title: string;
  content?: string;
  claims?: Claim[];
  subsections?: ReportSection[];
}

export interface Claim {
  id?: string;
  content: string;
  evidence_ids?: string[];
  confidence?: number;
  category?: string;
}

export interface Source {
  id: string;
  task_id: string;
  type: string;
  url: string | null;
  title: string;
  content_snippet: string;
  reliability_score?: number | null;
  included_in_analysis: boolean;
  curation_reason: string;
  curation_tags: string[];
  curated_excerpt: string;
  fetched_at: string;
}

export interface Metrics {
  id: string;
  task_id: string;
  source_count: number;
  claim_count: number;
  evidence_coverage_rate: number;
  quality_score: number;
  quality_breakdown: Record<string, unknown>;
  manual_correction_count: number;
  calculated_at: string;
}

export interface TraceEvent {
  id?: string;
  agent_name: string;
  event_type: string;
  timestamp?: string;
  input_summary?: string | null;
  output_summary?: string | null;
  token_count?: number | null;
  error_message?: string | null;
  prompt?: string | null;
  input_data?: Record<string, unknown> | null;
  output_data?: Record<string, unknown> | null;
  duration?: number | null;
  retry_attempt?: number | null;
}

export interface Trace {
  id: string;
  task_id: string;
  agent_name: string;
  events: TraceEvent[];
  total_duration: number | null;
  total_tokens: number | null;
  status: string;
}

export interface CorrectionPayload {
  correction_type: "add_source" | "edit_claim" | "add_constraint";
  data: Record<string, unknown>;
}

export interface ConstraintSummary {
  id: string;
  constraint_type: string;
  constraint_value: string;
  applied_to: string;
  created_at: string;
}

export interface RunHistorySummary {
  id: string;
  run_index: number;
  status: string;
  retry_count: number;
  source_count: number;
  claim_count: number;
  evidence_coverage_rate: number;
  quality_score: number;
  quality_breakdown: Record<string, unknown>;
  manual_correction_count: number;
  created_at: string;
  qa_feedback: Record<string, unknown>;
  curation_summary: CurationSummary;
}

export interface RunHistoryDelta {
  source_count_delta: number;
  claim_count_delta: number;
  evidence_coverage_delta: number;
  quality_score_delta: number;
  retry_count_delta: number;
  manual_correction_delta: number;
}

export interface RunHistoryCompareResponse {
  current: RunHistorySummary;
  previous: RunHistorySummary | null;
  delta: RunHistoryDelta | null;
}

export interface SSEEvent {
  agent: string;
  status: string;
  duration?: number | null;
  tokens?: number | null;
  passed?: boolean | null;
  retry_target?: string | null;
  retry_count?: number | null;
  evidence_coverage_rate?: number | null;
  removed_claims?: number | null;
}

export const taskApi = {
  create: (data: TaskCreatePayload) => api.post<Task>("/tasks", data),
  overview: () => api.get<TaskOverviewResponse>("/tasks/overview"),
  list: () => api.get<Task[]>("/tasks"),
  get: (id: string) => api.get<Task>(`/tasks/${id}`),
  run: (id: string) => api.post<{ message: string; task_id: string }>(`/tasks/${id}/run`),
  continueAfterReview: (id: string, instruction = "") =>
    api.post<{ message: string; task_id: string }>(`/tasks/${id}/continue`, { instruction }),
  getStatus: (id: string) => api.get<{ id: string; status: string; target_product: string }>(`/tasks/${id}/status`),
  submitCorrection: (id: string, correction: CorrectionPayload) =>
    api.post<{ message: string; task_id: string }>(`/tasks/${id}/corrections`, correction),
  constraints: (id: string) => api.get<ConstraintSummary[]>(`/tasks/${id}/constraints`),
  runs: (id: string) => api.get<RunHistorySummary[]>(`/tasks/${id}/runs`),
  compareLatestRuns: (id: string) => api.get<RunHistoryCompareResponse>(`/tasks/${id}/runs/latest/compare`),
  rerun: (id: string) => api.post<{ message: string; task_id: string }>(`/tasks/${id}/rerun`),
};

export const reportApi = {
  get: (taskId: string) => api.get<Report>(`/tasks/${taskId}/report`),
  exportUrl: (taskId: string, format: ReportExportFormat) =>
    `/api/tasks/${taskId}/export?format=${encodeURIComponent(format)}`,
};

export const sourceApi = {
  list: (taskId: string) => api.get<Source[]>(`/tasks/${taskId}/sources`),
  get: (taskId: string, sourceId: string) => api.get<Source>(`/tasks/${taskId}/sources/${sourceId}`),
};

export const metricsApi = {
  get: (taskId: string) => api.get<Metrics>(`/tasks/${taskId}/metrics`),
};

export const traceApi = {
  list: (taskId: string) => api.get<Trace[]>(`/tasks/${taskId}/traces`),
};

export interface DemoScenarioSummary {
  id: string;
  name: string;
  description: string;
  industry: string;
  target_product: string;
  competitors: { name: string; category: string; website?: string }[];
  focus_areas: string[];
}

export interface DemoSource {
  id: string;
  type: string;
  url: string | null;
  title: string;
  content_snippet: string;
  reliability_score: number | null;
}

export interface DemoTrace {
  agent_name: string;
  events: Record<string, unknown>[];
  total_duration: number | null;
  total_tokens: number | null;
  status: string;
}

export interface DemoMetrics {
  source_count: number;
  claim_count: number;
  evidence_coverage_rate: number;
  manual_correction_count: number;
}

export interface DemoScenarioDetail extends DemoScenarioSummary {
  our_product_notes: string;
  sources: DemoSource[];
  report: ReportContent;
  traces: DemoTrace[];
  metrics: DemoMetrics;
  analysis?: AnalysisData;
}

export const demoApi = {
  list: () => api.get<DemoScenarioSummary[]>("/demos"),
  get: (id: string) => api.get<DemoScenarioDetail>(`/demos/${id}`),
};

export interface DagNode {
  id: string;
  label: string;
  type: string; // "agent" | "tool"
  status: string; // "pending" | "running" | "completed" | "failed"
}

export interface DagEdge {
  source: string;
  target: string;
  label?: string | null;
}

export interface DagStructure {
  nodes: DagNode[];
  edges: DagEdge[];
}

export const dagApi = {
  get: (taskId: string) => api.get<DagStructure>(`/tasks/${taskId}/dag`),
};

// ---------------------------------------------------------------------------
// Survey & Interview
// ---------------------------------------------------------------------------

export interface SurveyQuestion {
  id: string;
  type: string; // "single_choice" | "multiple_choice" | "likert_scale" | "open_ended" | "ranking"
  text: string;
  options: string[];
  target_persona: string;
  dimension: string;
}

export interface SurveyData {
  title: string;
  description: string;
  questions: SurveyQuestion[];
  target_audience: string;
  estimated_duration_min: number;
}

export interface InterviewQuestion {
  id: string;
  phase: string; // "opening" | "core" | "probing" | "closing"
  text: string;
  follow_ups: string[];
  target_persona: string;
  dimension: string;
}

export interface InterviewData {
  title: string;
  target_persona: string;
  opening_script: string;
  questions: InterviewQuestion[];
  closing_script: string;
  estimated_duration_min: number;
  notes: string;
}

export const surveyApi = {
  get: (taskId: string) => api.get<SurveyData>(`/tasks/${taskId}/survey`),
};

export const interviewApi = {
  get: (taskId: string) => api.get<InterviewData>(`/tasks/${taskId}/interview`),
};

// ---------------------------------------------------------------------------
// Structured analysis — feature trees / pricing / personas / SWOT
// (powers the comparison matrix & SWOT quadrants)
// ---------------------------------------------------------------------------

export interface FeatureNode {
  name: string;
  description?: string;
  status: string; // "supported" | "partial" | "missing"
  children?: FeatureNode[];
}

export interface FeatureTree {
  product_name: string;
  root_nodes: FeatureNode[];
}

export interface PricingTier {
  name: string;
  price: number;
  currency?: string;
  period?: string;
  features?: string[];
  limitations?: string[];
}

export interface PricingModel {
  product_name: string;
  model_type: string;
  tiers: PricingTier[];
}

export interface Persona {
  segment_name: string;
  demographics?: string;
  pain_points?: string[];
  needs?: string[];
  product_usage_patterns?: string;
}

export interface SWOTItem {
  category: string; // "strength" | "weakness" | "opportunity" | "threat"
  content: string;
  evidence_ids?: string[];
}

export interface SWOTAnalysis {
  product_name: string;
  items: SWOTItem[];
}

export interface AnalysisData {
  feature_trees: FeatureTree[];
  pricing_models: PricingModel[];
  personas: Persona[];
  swot_analyses: SWOTAnalysis[];
}

export const analysisApi = {
  get: (taskId: string) => api.get<AnalysisData>(`/tasks/${taskId}/analysis`),
};

export const healthApi = {
  check: () => api.get<{ status: string }>("/health"),
};

export default api;
