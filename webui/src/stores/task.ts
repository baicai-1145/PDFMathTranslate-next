import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { TaskDetail, TaskSummary, TaskStatus } from '@/types/task';
import { createTask, downloadTaskResult, getTask, listTasks } from '@/services/api';

const POLL_INTERVAL = 8000;

type ResultMode = 'mono' | 'dual' | 'original';

export const useTaskStore = defineStore('tasks', () => {
  const tasks = ref<TaskSummary[]>([]);
  const currentTask = ref<TaskDetail | null>(null);
  const currentTaskId = ref<string | null>(null);
  const loading = ref(false);
  const uploading = ref(false);
  const lastUpdated = ref<number | null>(null);
  const errorMessage = ref<string | null>(null);
  const infoMessage = ref<string | null>(null);
  const previewUrls = ref<Record<string, string>>({});
  let pollTimer: ReturnType<typeof setInterval> | null = null;

  const hasTasks = computed(() => tasks.value.length > 0);

  function setMessage(message: string, type: 'error' | 'info' = 'info') {
    if (type === 'error') {
      errorMessage.value = message;
    } else {
      infoMessage.value = message;
    }
    if (type === 'info') {
      setTimeout(() => (infoMessage.value = null), 3500);
    }
  }

  async function fetchTasks(limit?: number) {
    loading.value = true;
    try {
      tasks.value = await listTasks(limit);
      lastUpdated.value = Date.now();
      errorMessage.value = null;
      if (currentTaskId.value) {
        const match = tasks.value.find((item) => item.id === currentTaskId.value);
        if (match && (!currentTask.value || match.updated_at !== currentTask.value.updated_at)) {
          await fetchTaskDetail(match.id, { silent: true });
        }
      }
    } catch (error) {
      console.error(error);
      setMessage('加载任务列表失败，请稍后重试。', 'error');
    } finally {
      loading.value = false;
    }
  }

  async function fetchTaskDetail(id: string, options?: { silent?: boolean }) {
    try {
      if (!options?.silent) {
        loading.value = true;
      }
      const detail = await getTask(id);
      currentTask.value = detail;
      currentTaskId.value = id;
      const index = tasks.value.findIndex((item) => item.id === id);
      if (index >= 0) {
        tasks.value[index] = detail;
      } else {
        tasks.value.unshift(detail);
      }
    } catch (error) {
      console.error(error);
      setMessage('获取任务详情失败。', 'error');
    } finally {
      if (!options?.silent) {
        loading.value = false;
      }
    }
  }

  async function submitTask(file: File, config: Record<string, unknown>) {
    uploading.value = true;
    errorMessage.value = null;
    try {
      const detail = await createTask(file, config);
      currentTask.value = detail;
      currentTaskId.value = detail.id;
      tasks.value = [detail, ...tasks.value];
      setMessage('任务已创建，稍后刷新即可查看进度。');
      startPolling();
      return detail;
    } catch (error: any) {
      console.error(error);
      const msg =
        error?.response?.data?.detail ||
        error?.message ||
        '任务创建失败，请检查配置或稍后重试。';
      setMessage(msg, 'error');
      throw error;
    } finally {
      uploading.value = false;
    }
  }

  async function downloadResult(id: string, mode: 'mono' | 'dual' | 'original' = 'mono') {
    const blob = await downloadTaskResult(id, mode);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${id}-${mode}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  function previewKey(id: string, mode: ResultMode) {
    return `${id}:${mode}`;
  }

  async function ensurePreviewUrl(id: string, mode: ResultMode) {
    const key = previewKey(id, mode);
    if (!previewUrls.value[key]) {
      const blob = await downloadTaskResult(id, mode);
      const url = window.URL.createObjectURL(blob);
      previewUrls.value[key] = url;
      previewUrls.value = { ...previewUrls.value };
    }
    return previewUrls.value[key];
  }

  function releasePreviewUrls(keys?: string[]) {
    const urls = previewUrls.value;
    if (keys?.length) {
      for (const key of keys) {
        const url = urls[key];
        if (url) {
          window.URL.revokeObjectURL(url);
          delete urls[key];
        }
      }
    } else {
      for (const key in urls) {
        if (Object.prototype.hasOwnProperty.call(urls, key)) {
          window.URL.revokeObjectURL(urls[key]);
          delete urls[key];
        }
      }
    }
    previewUrls.value = { ...urls };
  }

  function startPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
    }
    pollTimer = setInterval(() => {
      void fetchTasks();
    }, POLL_INTERVAL);
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function humanStatus(status: TaskStatus) {
    switch (status) {
      case 'PENDING':
        return '排队中';
      case 'RUNNING':
        return '处理中';
      case 'DONE':
        return '完成';
      case 'FAILED':
        return '失败';
      default:
        return status;
    }
  }

  return {
    tasks,
    currentTask,
    currentTaskId,
    loading,
    uploading,
    hasTasks,
    lastUpdated,
    errorMessage,
    infoMessage,
    previewUrls,
    fetchTasks,
    fetchTaskDetail,
    submitTask,
    downloadResult,
    ensurePreviewUrl,
    releasePreviewUrls,
    startPolling,
    stopPolling,
    setMessage,
    clearError() {
      errorMessage.value = null;
    },
    humanStatus
  };
});
