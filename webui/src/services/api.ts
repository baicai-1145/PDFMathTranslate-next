import axios from 'axios';
import type { TaskDetail, TaskSummary } from '@/types/task';

const baseURL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_BASE ||
  '/api';

export const apiClient = axios.create({
  baseURL,
  timeout: 60_000
});

export async function listTasks(limit = 50): Promise<TaskSummary[]> {
  const { data } = await apiClient.get<TaskSummary[]>('/tasks', {
    params: { limit }
  });
  return data;
}

export async function createTask(
  file: File,
  config: Record<string, unknown>
): Promise<TaskDetail> {
  const form = new FormData();
  form.append('file', file);
  form.append('config', JSON.stringify(config ?? {}));

  const { data } = await apiClient.post<TaskDetail>('/tasks', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return data;
}

export async function getTask(id: string): Promise<TaskDetail> {
  const { data } = await apiClient.get<TaskDetail>(`/tasks/${id}`);
  return data;
}

export async function downloadTaskResult(
  id: string,
  mode: 'mono' | 'dual' | 'original' = 'mono'
): Promise<Blob> {
  const { data } = await apiClient.get(`/tasks/${id}/result`, {
    params: { mode },
    responseType: 'blob'
  });
  return data;
}
