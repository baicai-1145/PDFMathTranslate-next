<template>
  <div class="dashboard-shell">
    <main-top-bar
      :is-dark="isDark"
      @toggle-dark="toggleDark"
      @refresh="refreshTasks"
      @toggle-locale="toggleLocale"
      :locale="locale"
    />

    <transition name="slide-down">
      <div v-if="taskStore.errorMessage" class="alert alert-error">
        {{ taskStore.errorMessage }}
      </div>
    </transition>
    <transition name="slide-down">
      <div v-if="taskStore.infoMessage" class="alert alert-info">
        {{ taskStore.infoMessage }}
      </div>
    </transition>

    <div class="dashboard-body">
      <aside class="sidebar">
        <upload-panel />
        <task-list />
      </aside>
      <task-detail class="main-panel" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { onMounted, onBeforeUnmount } from 'vue';
import MainTopBar from '@/components/layout/MainTopBar.vue';
import { useThemeStore } from '@/stores/theme';
import UploadPanel from '@/components/upload/UploadPanel.vue';
import TaskList from '@/components/task/TaskList.vue';
import TaskDetail from '@/components/task/TaskDetail.vue';
import { useTaskStore } from '@/stores/task';
import { useI18n } from '@/i18n';

const taskStore = useTaskStore();
const themeStore = useThemeStore();
const { isDark } = storeToRefs(themeStore);
const { locale, toggleLocale } = useI18n();

const toggleDark = () => {
  themeStore.toggleTheme();
};

const refreshTasks = () => {
  void taskStore.fetchTasks();
};

onMounted(() => {
  void taskStore.fetchTasks();
  taskStore.startPolling();
});

onBeforeUnmount(() => {
  taskStore.stopPolling();
});
</script>

<style scoped>
.dashboard-shell {
  min-height: 100vh;
  background: var(--surface-primary);
  color: var(--text-primary);
  display: flex;
  flex-direction: column;
}

.dashboard-body {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1.5rem 2rem 2rem;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.main-panel {
  flex: 1;
}

.dashboard-body {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 1.5rem;
}

.alert {
  margin: 0 auto;
  padding: 0.85rem 1.25rem;
  border-radius: 1rem;
  max-width: 720px;
  width: 100%;
  display: flex;
  justify-content: center;
  font-size: 0.9rem;
  border: 1px solid transparent;
}

.alert-info {
  background: rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.25);
  color: #1d4ed8;
}

.alert-error {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.3);
  color: #b91c1c;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.slide-down-leave-active {
  transition-duration: 0.18s;
}

@media (max-width: 1024px) {
  .dashboard-body {
    grid-template-columns: 1fr;
  }
}
</style>
