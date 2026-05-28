import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

export interface Task {
  id: string;
  industry: string;
  target_product: string;
  competitors: string[];
  status: string;
  created_at: string;
  updated_at: string;
}

export interface TaskCreatePayload {
  industry?: string;
  target_product: string;
  competitors?: string[];
}

export interface Report {
  id: string;
  task_id: string;
  title: string;
  content: ReportContent;
  status: string;
  created_at: string;
}

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
  fetched_at: string;
}

export interface Metrics {
  id: string;
  task_id: string;
  source_count: number;
  claim_count: number;
  evidence_coverage_rate: number;
  manual_correction_count: number;
  calculated_at: string;
}

export interface Trace {
  id: string;
  task_id: string;
  agent_name: string;
  events: unknown[];
  total_duration: number | null;
  total_tokens: number | null;
  status: string;
}

export const taskApi = {
  create: (data: TaskCreatePayload) => api.post<Task>("/tasks", data),
  list: () => api.get<Task[]>("/tasks"),
  get: (id: string) => api.get<Task>(`/tasks/${id}`),
  run: (id: string) => api.post<{ message: string; task_id: string }>(`/tasks/${id}/run`),
  getStatus: (id: string) => api.get<{ id: string; status: string; target_product: string }>(`/tasks/${id}/status`),
};

export const reportApi = {
  get: (taskId: string) => api.get<Report>(`/tasks/${taskId}/report`),
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

export const healthApi = {
  check: () => api.get<{ status: string }>("/health"),
};

export default api;
