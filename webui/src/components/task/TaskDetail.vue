<template>
<section class="detail card">
    <header class="header">
      <div>
        <h2>{{ currentTask?.filename || t('main.chooseTask') }}</h2>
        <p v-if="currentTask" class="muted">
          {{ t('task.createdAt') }} {{ formatTime(currentTask.created_at) }} ·
          {{ t('task.lastUpdated') }} {{ formatTime(currentTask.updated_at) }}
        </p>
      </div>
      <status-badge v-if="currentTask" :status="currentTask.status" />
    </header>

    <div v-if="!currentTask" class="empty">
      {{ t('main.chooseTask') }}
    </div>

    <div v-else class="content">
      <section class="preview">
        <div class="preview-header">
          <h3>{{ t('preview.title') }}</h3>
          <div class="controls">
            <button
              class="btn-secondary"
              :disabled="!canPreviewMono"
              @click="showMonoPreview"
            >
              {{ t('preview.single') }}
            </button>
            <button
              class="btn-secondary"
              :disabled="!canPreviewDual"
              @click="showDualPreview"
            >
              {{ t('preview.dual') }}
            </button>
            <button
              v-if="previewMode !== 'none'"
              class="btn-secondary"
              @click="closePreview"
            >
              {{ t('preview.close') }}
            </button>
          </div>
        </div>
        <div v-if="previewError" class="alert">
          {{ previewError }}
        </div>
        <div v-else-if="previewLoading" class="placeholder">
          {{ t('preview.loading') }}
        </div>
        <div v-else-if="previewMode === 'mono'" class="preview-single">
          <iframe v-if="monoPreviewUrl" :src="monoPreviewUrl" title="翻译预览" />
        </div>
        <div v-else-if="previewMode === 'dual'" class="preview-dual">
          <div class="pane">
            <header>{{ t('preview.source') }}</header>
            <div class="viewer" ref="originalScroll">
              <iframe v-if="originalPreviewUrl" :src="originalPreviewUrl" title="原文预览" />
            </div>
          </div>
          <div class="pane">
            <header>{{ t('preview.target') }}</header>
            <div class="viewer" ref="monoScroll">
              <iframe v-if="monoPreviewUrl" :src="monoPreviewUrl" title="译文预览" />
            </div>
          </div>
        </div>
        <div v-else class="placeholder">
          {{ t('preview.prompt') }}
        </div>
      </section>

      <section class="summary">
        <div class="summary-header">
          <h3>{{ t('main.summary') }}</h3>
          <div class="downloads">
            <button
              class="btn-primary"
              :disabled="!currentTask.result?.mono_pdf || currentTask.status !== 'DONE'"
              @click="download('mono')"
            >
              {{ t('main.downloadMono') }}
            </button>
            <button
              class="btn-secondary"
              :disabled="!currentTask.result?.dual_pdf || currentTask.status !== 'DONE'"
              @click="download('dual')"
            >
              {{ t('main.downloadDual') }}
            </button>
            <button
              class="btn-secondary"
              :disabled="!currentTask.result?.original_pdf"
              @click="download('original')"
            >
              {{ t('main.downloadOriginal') }}
            </button>
          </div>
        </div>
        <p>
          {{ t('main.status') }}：{{ humanStatus(currentTask.status) }}
        </p>
        <p v-if="currentTask.message">
          {{ currentTask.message }}
        </p>
        <p v-else-if="currentTask.status !== 'DONE'">
          {{ t('main.inProgress') }}
        </p>
        <div class="progress-bar">
          <div class="progress" :style="{ width: `${progressPercent(currentTask)}%` }" />
        </div>
      </section>

      <section class="events">
        <h3>{{ t('main.events') }}</h3>
        <ul>
          <li v-for="(event, index) in reversedEvents" :key="index">
            <strong>{{ event.type }}</strong>
            <span v-if="event.progress !== undefined">
              · {{ t('main.progress') }} {{ Math.round((event.progress ?? 0) * 100) }}%
            </span>
            <span v-if="event.error">
              · {{ event.error }}
            </span>
          </li>
        </ul>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { computed, ref, watch, onBeforeUnmount, onMounted, nextTick } from 'vue';
import { useTaskStore } from '@/stores/task';
import { useI18n } from '@/i18n';
import StatusBadge from '@/components/task/TaskStatusBadge.vue';
import throttle from 'lodash.throttle';

const taskStore = useTaskStore();
const { currentTask } = storeToRefs(taskStore);
const { t } = useI18n();

const humanStatus = (status: any) => taskStore.humanStatus(status);

const reversedEvents = computed(() => {
  return currentTask.value?.events ? [...currentTask.value.events].reverse() : [];
});

const previewMode = ref<'none' | 'mono' | 'dual'>('none');
const previewLoading = ref(false);
const previewError = ref<string | null>(null);
const monoPreviewUrl = ref<string | null>(null);
const originalPreviewUrl = ref<string | null>(null);
const monoScroll = ref<HTMLDivElement | null>(null);
const originalScroll = ref<HTMLDivElement | null>(null);
const isSyncing = ref(false);

const canPreviewMono = computed(() => Boolean(currentTask.value?.result?.mono_pdf));
const canPreviewDual = computed(
  () => Boolean(currentTask.value?.result?.mono_pdf && currentTask.value?.result?.original_pdf)
);

watch(
  () => currentTask.value?.id,
  () => {
    taskStore.releasePreviewUrls();
    detachSync();
    previewMode.value = 'none';
    previewError.value = null;
    monoPreviewUrl.value = null;
    originalPreviewUrl.value = null;
  }
);

watch(
  previewMode,
  async (mode) => {
    if (mode === 'dual') {
      await nextTick();
      attachSync();
    } else {
      detachSync();
    }
  }
);

function formatTime(value: string | number | null | undefined) {
  if (!value) return '--';
  const date = typeof value === 'number' ? new Date(value) : new Date(value);
  return date.toLocaleString();
}

const download = (mode: 'mono' | 'dual' | 'original') => {
  if (!currentTask.value) return;
  void taskStore.downloadResult(currentTask.value.id, mode);
};

function progressPercent(task: { progress: number }) {
  const raw = typeof task.progress === 'number' ? task.progress : 0;
  const bounded = Math.min(Math.max(raw, 0), 1);
  return Math.round(bounded * 100);
}

async function showMonoPreview() {
  if (!currentTask.value) return;
  previewLoading.value = true;
  previewError.value = null;
  try {
    const url = await taskStore.ensurePreviewUrl(currentTask.value.id, 'mono');
    monoPreviewUrl.value = url;
    previewMode.value = 'mono';
    await nextTick();
    attachSync();
  } catch (error: any) {
    previewError.value = error?.response?.data?.detail || error?.message || '加载预览失败';
  } finally {
    previewLoading.value = false;
  }
}

async function showDualPreview() {
  if (!currentTask.value) return;
  previewLoading.value = true;
  previewError.value = null;
  try {
    const [originalUrl, monoUrl] = await Promise.all([
      taskStore.ensurePreviewUrl(currentTask.value.id, 'original'),
      taskStore.ensurePreviewUrl(currentTask.value.id, 'mono')
    ]);
    originalPreviewUrl.value = originalUrl;
    monoPreviewUrl.value = monoUrl;
    previewMode.value = 'dual';
    await nextTick();
    attachSync();
  } catch (error: any) {
    previewError.value = error?.response?.data?.detail || error?.message || '加载预览失败';
  } finally {
    previewLoading.value = false;
  }
}

function closePreview() {
  previewMode.value = 'none';
  detachSync();
}

onBeforeUnmount(() => {
  detachSync();
  taskStore.releasePreviewUrls();
});

const syncScroll = throttle((source: HTMLElement, target: HTMLElement) => {
  if (isSyncing.value) return;
  isSyncing.value = true;
  const ratio = source.scrollTop / (source.scrollHeight - source.clientHeight || 1);
  const targetScrollTop = ratio * (target.scrollHeight - target.clientHeight);
  target.scrollTop = targetScrollTop;
  requestAnimationFrame(() => {
    isSyncing.value = false;
  });
}, 50);

function handleMonoScroll() {
  if (previewMode.value !== 'dual') return;
  const monoEl = monoScroll.value;
  const originalEl = originalScroll.value;
  if (monoEl && originalEl) {
    syncScroll(monoEl, originalEl);
  }
}

function handleOriginalScroll() {
  if (previewMode.value !== 'dual') return;
  const monoEl = monoScroll.value;
  const originalEl = originalScroll.value;
  if (monoEl && originalEl) {
    syncScroll(originalEl, monoEl);
  }
}

function attachSync() {
  detachSync();
  const monoEl = monoScroll.value;
  const originalEl = originalScroll.value;
  if (monoEl) {
    monoEl.addEventListener('scroll', handleMonoScroll);
  }
  if (originalEl) {
    originalEl.addEventListener('scroll', handleOriginalScroll);
  }
}

function detachSync() {
  const monoEl = monoScroll.value;
  const originalEl = originalScroll.value;
  if (monoEl) {
    monoEl.removeEventListener('scroll', handleMonoScroll);
  }
  if (originalEl) {
    originalEl.removeEventListener('scroll', handleOriginalScroll);
  }
}
</script>

<style scoped>
.detail {
  padding: 1.5rem;
  min-height: 560px;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  background: var(--surface-elevated);
}

.header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.header h2 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.muted {
  margin-top: 0.35rem;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.empty {
  margin: auto;
  color: var(--text-muted);
}

.content {
  display: grid;
  grid-template-columns: 2.5fr 1fr;
  gap: 1.5rem;
  align-items: start;
}

.summary,
.preview,
.events {
  background: var(--surface-muted);
  padding: 1.25rem;
  border-radius: 1.15rem;
  border: 1px solid var(--border-muted);
}

.summary h3,
.preview h3,
.events h3 {
  margin: 0 0 1rem;
  font-size: 0.95rem;
  font-weight: 600;
}

.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.summary .downloads {
  display: flex;
  gap: 0.4rem;
}

.summary .downloads button {
  min-width: 0;
  padding-inline: 0.85rem;
  font-size: 0.82rem;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.controls {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.alert {
  margin-top: 0.75rem;
  padding: 0.85rem 1rem;
  background: rgba(239, 68, 68, 0.15);
  border-radius: 0.9rem;
  color: #b91c1c;
  font-size: 0.85rem;
}

.placeholder {
  margin-top: 1rem;
  padding: 1.5rem;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.9rem;
  border-radius: 0.9rem;
  background: rgba(148, 163, 184, 0.12);
}

.preview-single,
.preview-dual {
  margin-top: 1rem;
}

.preview-single iframe,
.preview-dual iframe {
  border: none;
  width: 100%;
  height: 100%;
  border-radius: 0.75rem;
  background: #fff;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.2);
}

.preview-single iframe {
  min-height: 640px;
}

.preview-dual {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  min-height: 640px;
}

.preview-dual .viewer {
  position: relative;
  height: 640px;
  border-radius: 0.75rem;
  overflow-y: auto;
  background: #f8fafc;
}

.preview-dual .pane {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.preview-dual .pane header {
  font-weight: 600;
  color: var(--text-secondary);
}

.progress-bar {
  margin-top: 1rem;
  height: 8px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.2);
  overflow: hidden;
}

.progress {
  height: 100%;
  background: var(--accent);
  transition: width 0.3s ease;
}

.events ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.events li {
  padding: 0.75rem;
  border-radius: 0.9rem;
  background: rgba(148, 163, 184, 0.12);
}

@media (min-width: 1024px) {
  .content {
    grid-template-columns: 2.5fr 1fr;
  }
}

@media (max-width: 1024px) {
  .content {
    grid-template-columns: 1fr;
  }

  .summary-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .summary .downloads {
    width: 100%;
    flex-wrap: wrap;
  }

  .summary .downloads button {
    flex: 1 1 45%;
  }

  .preview-dual {
    grid-template-columns: 1fr;
  }

  .preview-dual .viewer {
    height: 480px;
  }
}
</style>
