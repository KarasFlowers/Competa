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

export const taskApi = {
  create: (data: TaskCreatePayload) => api.post<Task>("/tasks", data),
  list: () => api.get<Task[]>("/tasks"),
  get: (id: string) => api.get<Task>(`/tasks/${id}`),
};

export const healthApi = {
  check: () => api.get<{ status: string }>("/health"),
};

export default api;
