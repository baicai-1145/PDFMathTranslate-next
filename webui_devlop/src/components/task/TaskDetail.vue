<template>
  <section class="detail card">
    <header class="header">
      <div class="title-block">
        <h2>{{ currentTask?.filename || t('main.chooseTask') }}</h2>
        <p v-if="currentTask" class="muted">
          {{ t('task.createdAt') }} {{ formatTime(currentTask.created_at) }} ·
          {{ t('task.lastUpdated') }} {{ formatTime(currentTask.updated_at) }}
        </p>
      </div>
      <div v-if="currentTask" class="header-actions">
        <status-badge :status="currentTask.status" />
        <div class="header-buttons" ref="downloadMenuRef">
          <button
            class="download-trigger"
            :disabled="!hasDownloadable"
            @click.stop="toggleDownloadMenu"
          >
            {{ t('main.downloads') }}
          </button>
          <div v-if="showDownloadMenu" class="download-menu">
            <button
              class="download-menu__item"
              :disabled="!canDownloadMono"
              @click="handleDownload('mono')"
            >
              {{ t('main.downloadMono') }}
            </button>
            <button
              class="download-menu__item"
              :disabled="!canDownloadDual"
              @click="handleDownload('dual')"
            >
              {{ t('main.downloadDual') }}
            </button>
            <button
              class="download-menu__item"
              :disabled="!canDownloadOriginal"
              @click="handleDownload('original')"
            >
              {{ t('main.downloadOriginal') }}
            </button>
            <button
              class="download-menu__item"
              :disabled="!canDownloadZip"
              @click="handleDownloadZip"
            >
              {{ t('main.downloadZip') }}
            </button>
          </div>
        </div>
      </div>
    </header>

    <div v-if="!currentTask" class="empty">
      {{ t('main.chooseTask') }}
    </div>

    <template v-else>
      <div class="status-info">
        <span>{{ t('main.status') }}：{{ humanStatus(currentTask.status) }}</span>
        <span v-if="currentTask.message">· {{ currentTask.message }}</span>
        <span v-else-if="currentTask.status !== 'DONE'">· {{ t('main.inProgress') }}</span>
      </div>
      <div class="progress-bar">
        <div class="progress" :style="{ width: `${progressPercent(currentTask)}%` }" />
      </div>

      <div class="content">
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
            <PdfViewer
              v-if="monoPreviewUrl"
              ref="monoViewer"
              :url="monoPreviewUrl"
              @pdf-rendered="attachSync"
            />
          </div>
          <div v-else-if="previewMode === 'dual'" class="preview-dual">
            <div class="pane">
              <header>{{ t('preview.source') }}</header>
              <div class="viewer">
                <PdfViewer
                  v-if="originalPreviewUrl"
                  ref="originalViewer"
                  :url="originalPreviewUrl"
                  @pdf-rendered="attachSync"
                />
              </div>
            </div>
            <div class="pane">
              <header>{{ t('preview.target') }}</header>
              <div class="viewer">
                <PdfViewer
                  v-if="monoPreviewUrl"
                  ref="monoViewerDual"
                  :url="monoPreviewUrl"
                  @pdf-rendered="attachSync"
                />
              </div>
            </div>
          </div>
          <div v-else class="placeholder">
            {{ t('preview.prompt') }}
          </div>
        </section>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { computed, ref, watch, onBeforeUnmount, onMounted, nextTick } from 'vue';
import { useTaskStore } from '@/stores/task';
import { useI18n } from '@/i18n';
import StatusBadge from '@/components/task/TaskStatusBadge.vue';
import PdfViewer from '@/components/common/PdfViewer.vue';
import throttle from 'lodash.throttle';
const DEBUG_PREVIEW =
  String((import.meta.env as any).VITE_DEBUG_PREVIEW || '').toLowerCase() === 'true' ||
  import.meta.env.DEV;
function log(...args: unknown[]) {
  if (DEBUG_PREVIEW) console.debug('[TaskDetail]', ...args);
}

const taskStore = useTaskStore();
const { currentTask } = storeToRefs(taskStore);
const { t } = useI18n();

const humanStatus = (status: any) => taskStore.humanStatus(status);

const previewMode = ref<'none' | 'mono' | 'dual'>('none');
const previewLoading = ref(false);
const previewError = ref<string | null>(null);
const monoPreviewUrl = ref<string | null>(null);
const originalPreviewUrl = ref<string | null>(null);
const monoViewer = ref<InstanceType<typeof PdfViewer> | null>(null);
const monoViewerDual = ref<InstanceType<typeof PdfViewer> | null>(null);
const originalViewer = ref<InstanceType<typeof PdfViewer> | null>(null);
const isSyncing = ref(false);
let monoScroller: HTMLElement | null = null;
let originalScroller: HTMLElement | null = null;
let monoInnerScroller: HTMLElement | null = null;
let originalInnerScroller: HTMLElement | null = null;
let attachRetryTimer: number | null = null;
let attachRetryCount = 0;

const downloadMenuRef = ref<HTMLDivElement | null>(null);
const showDownloadMenu = ref(false);

const canPreviewMono = computed(() => Boolean(currentTask.value?.result?.mono_pdf));
const canPreviewDual = computed(
  () => Boolean(currentTask.value?.result?.mono_pdf && currentTask.value?.result?.original_pdf)
);

const canDownloadMono = computed(
  () =>
    Boolean(currentTask.value?.result?.mono_pdf) &&
    currentTask.value?.status === 'DONE'
);
const canDownloadDual = computed(
  () =>
    Boolean(currentTask.value?.result?.dual_pdf) &&
    currentTask.value?.status === 'DONE'
);
const canDownloadOriginal = computed(() => Boolean(currentTask.value?.result?.original_pdf));
const canDownloadZip = computed(
  () => Boolean(currentTask.value?.result?.output_dir) && currentTask.value?.status === 'DONE'
);
const hasDownloadable = computed(
  () => canDownloadMono.value || canDownloadDual.value || canDownloadOriginal.value || canDownloadZip.value
);

watch(
  () => currentTask.value?.id,
  () => {
    log('task changed, reset previews');
    taskStore.releasePreviewUrls();
    detachSync();
    previewMode.value = 'none';
    previewError.value = null;
    monoPreviewUrl.value = null;
    originalPreviewUrl.value = null;
    showDownloadMenu.value = false;
    // Auto open mono preview if available on task selection
    if (
      currentTask.value &&
      currentTask.value.status === 'DONE' &&
      canPreviewMono.value
    ) {
      log('auto open mono preview');
      void showMonoPreview();
    }
  }
);

watch(
  previewMode,
  async (mode) => {
    if (mode === 'dual') {
      await nextTick();
      log('enter dual preview, try attach sync');
      attachSync();
    } else {
      log('leave dual preview, detach');
      detachSync();
    }
  }
);

function formatTime(value: string | number | null | undefined) {
  if (!value) return '--';
  const date = typeof value === 'number' ? new Date(value) : new Date(value);
  return date.toLocaleString();
}

function download(mode: 'mono' | 'dual' | 'original') {
  if (!currentTask.value) return;
  void taskStore.downloadResult(currentTask.value.id, mode);
}

function handleDownload(mode: 'mono' | 'dual' | 'original') {
  if (mode === 'mono' && !canDownloadMono.value) return;
  if (mode === 'dual' && !canDownloadDual.value) return;
  if (mode === 'original' && !canDownloadOriginal.value) return;
  showDownloadMenu.value = false;
  download(mode);
}

function handleDownloadZip() {
  if (!currentTask.value) return;
  if (!canDownloadZip.value) return;
  showDownloadMenu.value = false;
  void taskStore.downloadArchive(currentTask.value.id);
}

function toggleDownloadMenu() {
  if (!hasDownloadable.value) return;
  showDownloadMenu.value = !showDownloadMenu.value;
}

function handleOutsideClick(event: MouseEvent) {
  const root = downloadMenuRef.value;
  if (!root) return;
  if (!root.contains(event.target as Node)) {
    showDownloadMenu.value = false;
  }
}

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
    log('loaded mono preview');
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
    log('dual urls ready, try attach sync');
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

onMounted(() => {
  document.addEventListener('click', handleOutsideClick);
});

onBeforeUnmount(() => {
  detachSync();
  taskStore.releasePreviewUrls();
  document.removeEventListener('click', handleOutsideClick);
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

function resolveScroller(componentRef: any): HTMLElement | null {
  const exposed = componentRef?.getScroller?.();
  if (exposed) return exposed as HTMLElement;
  const el = (componentRef as any)?.$el as HTMLElement | undefined;
  const findScrollContainer = (startEl: HTMLElement | null): HTMLElement | null => {
    let cur: HTMLElement | null = startEl;
    for (let i = 0; i < 5 && cur; i += 1) {
      const style = window.getComputedStyle(cur);
      const oy = style.overflowY;
      if (oy === 'auto' || oy === 'scroll') return cur;
      cur = (cur.parentElement as HTMLElement) || null;
    }
    return null;
  };
  const fromWrapper = findScrollContainer((el?.parentElement as HTMLElement) || el || null);
  const inner = (el?.querySelector?.('.pdf-scroller') as HTMLElement) || null;
  const chosen = fromWrapper || inner;
  if (DEBUG_PREVIEW) {
    log('resolveScroller', {
      fromWrapper: fromWrapper?.className,
      inner: inner?.className,
      chosen: chosen?.className
    });
  }
  return chosen;
}

function resolveContainers(componentRef: any): { outer: HTMLElement | null; inner: HTMLElement | null } {
  const el = (componentRef as any)?.$el as HTMLElement | undefined;
  const findScrollContainer = (startEl: HTMLElement | null): HTMLElement | null => {
    let cur: HTMLElement | null = startEl;
    for (let i = 0; i < 5 && cur; i += 1) {
      const style = window.getComputedStyle(cur);
      const oy = style.overflowY;
      if (oy === 'auto' || oy === 'scroll') return cur;
      cur = (cur.parentElement as HTMLElement) || null;
    }
    return null;
  };
  const outer = findScrollContainer((el?.parentElement as HTMLElement) || el || null);
  const inner = (el?.querySelector?.('.pdf-scroller') as HTMLElement) || null;
  if (DEBUG_PREVIEW) log('resolveContainers', { outer: outer?.className, inner: inner?.className });
  return { outer, inner };
}

function handleMonoScroll(evt?: Event) {
  if (previewMode.value !== 'dual') return;
  const source = (evt?.currentTarget as HTMLElement) || monoScroller || monoInnerScroller;
  const targetCandidateA = source === monoInnerScroller ? originalInnerScroller : originalScroller;
  const targetCandidateB = source === monoScroller ? originalScroller : originalInnerScroller;
  const target = targetCandidateA || targetCandidateB;
  if (source && target) {
    syncScroll(source, target);
    log('mono scroll -> sync');
  }
}

function handleOriginalScroll(evt?: Event) {
  if (previewMode.value !== 'dual') return;
  const source = (evt?.currentTarget as HTMLElement) || originalScroller || originalInnerScroller;
  const targetCandidateA = source === originalInnerScroller ? monoInnerScroller : monoScroller;
  const targetCandidateB = source === originalScroller ? monoScroller : monoInnerScroller;
  const target = targetCandidateA || targetCandidateB;
  if (source && target) {
    syncScroll(source, target);
    log('original scroll -> sync');
  }
}

function attachSync() {
  detachSync();
  if (previewMode.value !== 'dual') {
    return;
  }
  const resolveAndBind = () => {
    const monoComponent = monoViewerDual.value;
    const monoBoth = resolveContainers(monoComponent);
    const origBoth = resolveContainers(originalViewer.value);
    monoScroller = monoBoth.outer || monoBoth.inner;
    originalScroller = origBoth.outer || origBoth.inner;
    monoInnerScroller = monoBoth.inner;
    originalInnerScroller = origBoth.inner;
    if (!(monoScroller || monoInnerScroller) || !(originalScroller || originalInnerScroller)) return false;
    monoScroller && monoScroller.addEventListener('scroll', handleMonoScroll, { passive: true });
    monoInnerScroller && monoInnerScroller.addEventListener('scroll', handleMonoScroll, { passive: true });
    originalScroller && originalScroller.addEventListener('scroll', handleOriginalScroll, { passive: true });
    originalInnerScroller && originalInnerScroller.addEventListener('scroll', handleOriginalScroll, { passive: true });
    log('bind scroll listeners ok');
    return true;
  };
  if (resolveAndBind()) return;
  attachRetryCount = 0;
  attachRetryTimer = window.setInterval(() => {
    attachRetryCount += 1;
    log('retry attach', attachRetryCount);
    if (resolveAndBind() || attachRetryCount >= 30) {
      if (attachRetryTimer) {
        clearInterval(attachRetryTimer);
        attachRetryTimer = null;
        log('stop retry attach', attachRetryCount);
      }
    }
  }, 200);
}

function detachSync() {
  if (attachRetryTimer) {
    clearInterval(attachRetryTimer);
    attachRetryTimer = null;
  }
  if (monoScroller) {
    monoScroller.removeEventListener('scroll', handleMonoScroll);
  }
  if (monoInnerScroller) {
    monoInnerScroller.removeEventListener('scroll', handleMonoScroll);
  }
  if (originalScroller) {
    originalScroller.removeEventListener('scroll', handleOriginalScroll);
  }
  if (originalInnerScroller) {
    originalInnerScroller.removeEventListener('scroll', handleOriginalScroll);
  }
  monoScroller = null;
  originalScroller = null;
  monoInnerScroller = null;
  originalInnerScroller = null;
  log('detached scroll listeners');
}
</script>

<style scoped>
.detail {
  padding: 1.5rem;
  min-height: 560px;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  background: var(--surface-elevated);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.title-block h2 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.title-block {
  display: flex;
  flex-direction: column;
}

.muted {
  margin-top: 0.35rem;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.header-buttons {
  position: relative;
  display: flex;
  align-items: center;
}

.download-trigger {
  border-radius: 999px;
  border: 1px solid var(--border-muted);
  background: var(--surface-muted);
  color: var(--text-primary);
  padding: 0.4rem 0.95rem;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}

.download-trigger:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(59, 130, 246, 0.08);
}

.download-trigger:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.download-menu {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0;
  background: var(--surface-elevated);
  border: 1px solid var(--border-muted);
  border-radius: 0.85rem;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.12);
  display: flex;
  flex-direction: column;
  padding: 0.35rem;
  min-width: 180px;
  z-index: 12;
}

.download-menu__item {
  border: none;
  background: transparent;
  color: var(--text-primary);
  text-align: left;
  padding: 0.55rem 0.85rem;
  border-radius: 0.65rem;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}

.download-menu__item:hover:not(:disabled) {
  background: var(--surface-muted);
  color: var(--accent);
}

.download-menu__item:disabled {
  color: var(--text-muted);
  cursor: not-allowed;
}

.empty {
  margin: auto;
  color: var(--text-muted);
}

.status-info {
  font-size: 0.85rem;
  color: var(--text-secondary);
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.progress-bar {
  height: 4px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.2);
  overflow: hidden;
}

.progress {
  height: 100%;
  background: var(--accent);
  transition: width 0.3s ease;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.preview {
  background: var(--surface-muted);
  padding: 1.25rem;
  border-radius: 1.15rem;
  border: 1px solid var(--border-muted);
}

.preview h3 {
  margin: 0 0 1rem;
  font-size: 0.95rem;
  font-weight: 600;
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

.preview-single :deep(.pdf-viewer),
.preview-dual :deep(.pdf-viewer) {
  border: none;
  width: 100%;
  height: 100%;
  border-radius: 0.75rem;
  background: #fff;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.2);
}

.preview-single :deep(.pdf-viewer) {
  min-height: clamp(520px, 75vh, 1080px);
}

.preview-dual {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  min-height: 640px;
}

.preview-dual .viewer {
  position: relative;
  height: clamp(520px, 75vh, 1080px);
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

@media (max-width: 1200px) {
  .header-actions {
    gap: 0.5rem;
  }
}

@media (max-width: 1024px) {
  .header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .preview-dual {
    grid-template-columns: 1fr;
  }

  .preview-dual .viewer {
    height: 480px;
  }
}

@media (max-width: 768px) {
  .download-menu {
    min-width: 160px;
  }

  .preview-single :deep(.pdf-viewer) {
    min-height: clamp(420px, 65vh, 920px);
  }

  .preview-dual .viewer {
    height: clamp(380px, 65vh, 920px);
  }
}
</style>
