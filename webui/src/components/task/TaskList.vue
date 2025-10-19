<template>
  <section class="task-list card">
    <header class="list-header">
      <div>
        <h3>{{ t('task.listTitle') }}</h3>
        <p class="sub-text" v-if="lastUpdated">
          {{ t('task.lastUpdated') }}：{{ formatTime(lastUpdated) }}
        </p>
      </div>
      <button class="btn-secondary text-sm" @click="refresh">
        {{ t('task.refresh') }}
      </button>
    </header>

    <div v-if="loading" class="loading-state">
      <span class="spinner" /> Loading...
    </div>

    <div v-else-if="!hasTasks" class="empty">
      {{ t('task.empty') }}
    </div>

    <ul v-else class="list">
      <li
        v-for="task in tasks"
        :key="task.id"
        :class="['item', { active: task.id === currentTaskId }]"
        @click="select(task.id)"
      >
        <div class="item-header">
          <span class="task-name">{{ task.filename }}</span>
          <status-badge :status="task.status" />
        </div>
        <div class="meta">
          <span>{{ t('task.statusLabel') }} {{ humanStatus(task.status) }}</span>
          <span>{{ t('task.createdAt') }} {{ formatTime(task.created_at) }}</span>
        </div>
        <div class="progress-bar">
          <div class="progress" :style="{ width: `${progressPercent(task)}%` }" />
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { useTaskStore } from '@/stores/task';
import { useI18n } from '@/i18n';
import StatusBadge from '@/components/task/TaskStatusBadge.vue';
import type { TaskSummary } from '@/types/task';

const taskStore = useTaskStore();
const { tasks, loading, currentTaskId, hasTasks, lastUpdated } = storeToRefs(taskStore);
const { t } = useI18n();

const refresh = () => {
  void taskStore.fetchTasks();
};

const select = (id: string) => {
  void taskStore.fetchTaskDetail(id);
};

function humanStatus(status: string) {
  return taskStore.humanStatus(status as any);
}

function formatTime(value: string | number | null | undefined) {
  if (!value) return '--';
  const date = typeof value === 'number' ? new Date(value) : new Date(value);
  return date.toLocaleString();
}

function progressPercent(task: TaskSummary) {
  const raw = typeof task.progress === 'number' ? task.progress : 0;
  const bounded = Math.min(Math.max(raw, 0), 1);
  return Math.round(bounded * 100);
}
</script>

<style scoped>
.task-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.list-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.sub-text {
  margin: 0.35rem 0 0;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.loading-state,
.empty {
  padding: 2rem 0;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.9rem;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.item {
  padding: 0.85rem;
  border-radius: 1rem;
  border: 1px solid transparent;
  background: var(--surface-muted);
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease;
}

.item:hover {
  border-color: var(--border-muted);
  transform: translateY(-1px);
}

.item.active {
  border-color: var(--accent);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
}

.item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.task-name {
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 80%;
}

.meta {
  display: flex;
  justify-content: space-between;
  color: var(--text-muted);
  font-size: 0.75rem;
}

.progress-bar {
  margin-top: 0.65rem;
  height: 6px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.3);
  overflow: hidden;
}

.progress {
  height: 100%;
  background: var(--accent);
  transition: width 0.3s ease;
}

.spinner {
  display: inline-block;
  width: 1rem;
  height: 1rem;
  border: 2px solid rgba(148, 163, 184, 0.3);
  border-top-color: var(--accent);
  border-radius: 999px;
  animation: spin 0.8s linear infinite;
  margin-right: 0.5rem;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
