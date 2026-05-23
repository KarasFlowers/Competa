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
  content: Record<string, unknown>;
  status: string;
  created_at: string;
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
  run: (id: string) => api.post<Task>(`/tasks/${id}/run`),
};

export const reportApi = {
  get: (taskId: string) => api.get<Report>(`/tasks/${taskId}/report`),
};

export const sourceApi = {
  list: (taskId: string) => api.get<Source[]>(`/tasks/${taskId}/sources`),
};

export const traceApi = {
  list: (taskId: string) => api.get<Trace[]>(`/tasks/${taskId}/traces`),
};

export const healthApi = {
  check: () => api.get<{ status: string }>("/health"),
};

export default api;
