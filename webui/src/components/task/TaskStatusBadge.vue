<template>
  <span :class="['badge', statusClass]">
    {{ humanReadable }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { TaskStatus } from '@/types/task';
import { useTaskStore } from '@/stores/task';

const props = defineProps<{
  status: TaskStatus;
}>();

const taskStore = useTaskStore();

const humanReadable = computed(() => taskStore.humanStatus(props.status));

const statusClass = computed(() => {
  switch (props.status) {
    case 'DONE':
      return 'badge-success';
    case 'FAILED':
      return 'badge-danger';
    case 'RUNNING':
      return 'badge-warning';
    default:
      return 'badge-muted';
  }
});
</script>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.badge-success {
  background: rgba(34, 197, 94, 0.12);
  color: #15803d;
}

.badge-danger {
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
}

.badge-warning {
  background: rgba(249, 115, 22, 0.12);
  color: #c2410c;
}

.badge-muted {
  background: rgba(148, 163, 184, 0.18);
  color: var(--text-muted);
}

:root[data-theme='dark'] .badge-success {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
}

:root[data-theme='dark'] .badge-danger {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
}

:root[data-theme='dark'] .badge-warning {
  background: rgba(249, 115, 22, 0.2);
  color: #fb923c;
}
</style>
