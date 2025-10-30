export type TaskStatus = 'PENDING' | 'RUNNING' | 'DONE' | 'FAILED';

export interface TaskResult {
  original_pdf?: string | null;
  mono_pdf?: string | null;
  dual_pdf?: string | null;
  output_dir?: string | null;
}

export interface TaskEvent {
  type: string;
  progress?: number;
  error?: string;
  error_type?: string;
  details?: string;
  translate_result?: TaskResult | null;
  [key: string]: unknown;
}

export interface TaskSummary {
  id: string;
  filename: string;
  status: TaskStatus;
  progress: number;
  message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskDetail extends TaskSummary {
  events: TaskEvent[];
  result?: TaskResult | null;
}

export interface CreateTaskPayload {
  file: File;
  config: Record<string, unknown>;
}
