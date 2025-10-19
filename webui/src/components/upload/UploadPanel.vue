<template>
  <section class="upload-panel">
    <header class="section-header">
      <h2>{{ t('upload.title') }}</h2>
      <p class="muted-text">
        {{ t('upload.subtitle') }}
        <span class="highlight">{{ username }}</span>
      </p>
    </header>

    <label
      class="dropzone card outlined"
      @dragover.prevent
      @drop.prevent="handleDrop"
    >
      <input
        ref="fileInput"
        type="file"
        class="hidden-input"
        accept=".pdf,.PDF,image/*"
        @change="onFileChange"
      />
      <p>{{ t('upload.drop') }}</p>
      <p v-if="selectedFile" class="file-name">
        {{ selectedFile.name }}
      </p>
    </label>

    <div class="config-grid mt-4">
      <label class="field">
        <span>{{ t('upload.langFrom') }}</span>
        <select v-model="form.langFrom">
          <option value="en">English (en)</option>
          <option value="zh">中文 (zh)</option>
          <option value="ja">日本語 (ja)</option>
          <option value="de">Deutsch (de)</option>
          <option value="fr">Français (fr)</option>
        </select>
      </label>

      <label class="field">
        <span>{{ t('upload.langTo') }}</span>
        <select v-model="form.langTo">
          <option value="zh">中文 (zh)</option>
          <option value="en">English (en)</option>
          <option value="ja">日本語 (ja)</option>
          <option value="de">Deutsch (de)</option>
          <option value="fr">Français (fr)</option>
        </select>
      </label>
    </div>

    <button class="btn-secondary advanced-toggle" @click="toggleAdvanced">
      {{ t('upload.advanced') }} {{ showAdvanced ? '▾' : '▸' }}
    </button>

    <transition name="fade">
      <div v-if="showAdvanced" class="advanced card">
        <h4>{{ t('upload.serviceTitle') }}</h4>
        <label class="field">
          <span>SiliconFlow</span>
          <input
            v-model="form.siliconflowKey"
            :placeholder="t('upload.siliconflowKey')"
            type="password"
            autocomplete="off"
          />
        </label>
        <label class="field checkbox">
          <input v-model="form.remember" type="checkbox" />
          <span>{{ t('upload.rememberConfig') }}</span>
        </label>
      </div>
    </transition>

    <button
      class="btn-primary mt-4"
      :disabled="!selectedFile || taskStore.uploading"
      @click="submit"
    >
      <span v-if="taskStore.uploading">...</span>
      <span v-else>{{ t('upload.start') }}</span>
    </button>
  </section>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useTaskStore } from '@/stores/task';
import { useI18n } from '@/i18n';

const { t } = useI18n();
const taskStore = useTaskStore();

const fileInput = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const showAdvanced = ref(false);
const username = 'visitor';

const STORAGE_KEY = 'pdfmathtranslate-upload-config';

const form = reactive({
  langFrom: 'en',
  langTo: 'zh',
  siliconflowKey: '',
  remember: false
});

onMounted(() => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      form.langFrom = parsed.langFrom ?? form.langFrom;
      form.langTo = parsed.langTo ?? form.langTo;
      form.siliconflowKey = parsed.siliconflowKey ?? '';
      form.remember = Boolean(parsed.remember);
    }
  } catch (error) {
    console.warn('Failed to restore upload config', error);
  }
});

function handleDrop(event: DragEvent) {
  const files = event.dataTransfer?.files;
  if (files && files.length > 0) {
    selectedFile.value = files[0];
  }
}

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    selectedFile.value = target.files[0];
  }
}

function toggleAdvanced() {
  showAdvanced.value = !showAdvanced.value;
}

async function submit() {
  if (!selectedFile.value) {
    taskStore.setMessage('请先选择文件。', 'error');
    return;
  }

  const payload: Record<string, unknown> = {
    translation: {
      lang_in: form.langFrom,
      lang_out: form.langTo
    }
  };

  if (form.siliconflowKey.trim()) {
    payload.siliconflow = true;
    payload.siliconflow_detail = {
      siliconflow_api_key: form.siliconflowKey.trim()
    };
  }

  try {
    await taskStore.submitTask(selectedFile.value, payload);
    if (form.remember) {
      const snapshot = {
        langFrom: form.langFrom,
        langTo: form.langTo,
        siliconflowKey: form.siliconflowKey,
        remember: true
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
    if (fileInput.value) {
      fileInput.value.value = '';
    }
    selectedFile.value = null;
  } catch (error) {
    console.error(error);
  }
}
</script>

<style scoped>
.upload-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-header h2 {
  font-weight: 600;
  font-size: 1rem;
  margin: 0;
}

.muted-text {
  margin: 0.25rem 0 0;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.highlight {
  color: var(--accent);
  font-weight: 600;
}

.dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 120px;
  cursor: pointer;
}

.hidden-input {
  display: none;
}

.file-name {
  margin-top: 0.5rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-size: 0.9rem;
}

.field span {
  color: var(--text-secondary);
  font-weight: 500;
}

.field select,
.field input {
  border-radius: 0.75rem;
  border: 1px solid var(--border-muted);
  padding: 0.5rem 0.75rem;
  background: var(--surface-elevated);
  color: var(--text-primary);
  font-family: inherit;
}

.field.checkbox {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}

.advanced {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.advanced h4 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
}

.advanced-toggle {
  width: 100%;
  justify-content: center;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .config-grid {
    grid-template-columns: 1fr;
  }
}
</style>
