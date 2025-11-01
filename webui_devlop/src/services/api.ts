import axios from 'axios';
import type { TaskDetail, TaskSummary } from '@/types/task';
import type { AuthResponse, UserProfile } from '@/types/user';

// 优先使用显式后端地址，其次兼容旧变量，最后退回到 dev 代理路径 /api
// 与 webui 目录保持一致，避免环境变量名不一致导致误用本地代理
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
  mode: 'mono' | 'dual' | 'original' = 'mono',
  disposition: 'inline' | 'attachment' = 'attachment'
): Promise<Blob> {
  const { data } = await apiClient.get(`/tasks/${id}/result`, {
    params: { mode, disposition },
    responseType: 'blob'
  });
  return data;
}

export async function downloadTaskResultBase64(
  id: string,
  mode: 'mono' | 'dual' | 'original' = 'mono'
): Promise<{ filename: string; mime: string; data: string }>{
  const { data } = await apiClient.get(`/tasks/${id}/result`, {
    params: { mode, format: 'base64' }
  });
  return data as { filename: string; mime: string; data: string };
}

export async function downloadTaskArchive(id: string): Promise<Blob> {
  const { data } = await apiClient.get(`/tasks/${id}/archive`, {
    responseType: 'blob'
  });
  return data;
}

export async function getProfile(token?: string): Promise<UserProfile> {
  const headers = token
    ? {
        Authorization: `Bearer ${token}`
      }
    : undefined;
  const { data } = await apiClient.get<UserProfile>('/auth/me', {
    headers
  });
  return data;
}

export async function login(username: string, password: string): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/auth/login', {
    username,
    password
  });
  return data;
}

export async function register(username: string, password: string): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/auth/register', {
    username,
    password
  });
  return data;
}
