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

    

    <button
      class="btn-primary mt-4"
      :disabled="!selectedFile || taskStore.uploading"
      @click="submit"
    >
      <span v-if="taskStore.uploading">...</span>
      <span v-else>{{ t('upload.start') }}</span>
    </button>
    <p class="login-hint">
      {{ authStore.isLoggedIn ? t('upload.loggedInNote') : t('upload.guestNote') }}
    </p>
  </section>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue';
import { useTaskStore } from '@/stores/task';
import { useI18n } from '@/i18n';
import { useAuthStore } from '@/stores/auth';

const { t } = useI18n();
const taskStore = useTaskStore();
const authStore = useAuthStore();

const fileInput = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
// Advanced configuration was removed in server-deploy edition
const username = computed(() => authStore.displayName ?? t('auth.guest'));

const DEFAULT_DEEPSEEK_MODEL = 'deepseek-chat';

const form = reactive({
  langFrom: 'en',
  langTo: 'zh'
});

onMounted(() => {
  void authStore.initialize();
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

// Advanced toggle removed

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

  // Server-deploy edition: read provider from environment only
  const ENV_PROVIDER = String((import.meta.env as any).VITE_PROVIDER || '').toLowerCase();
  const ENV_SF_KEY = String((import.meta.env as any).VITE_SILICONFLOW_API_KEY || '');
  const ENV_DS_KEY = String((import.meta.env as any).VITE_DEEPSEEK_API_KEY || '');
  const ENV_DS_MODEL = String((import.meta.env as any).VITE_DEEPSEEK_MODEL || DEFAULT_DEEPSEEK_MODEL);
  const ENV_OC_BASE = String((import.meta.env as any).VITE_OPENAI_COMPAT_BASE_URL || '');
  const ENV_OC_KEY = String((import.meta.env as any).VITE_OPENAI_COMPAT_API_KEY || '');
  const ENV_OC_MODEL = String((import.meta.env as any).VITE_OPENAI_COMPAT_MODEL || 'gpt-4o-mini');

  if (ENV_PROVIDER === 'siliconflow' && ENV_SF_KEY) {
    payload.siliconflow = true;
    payload.siliconflow_detail = { siliconflow_api_key: ENV_SF_KEY };
  } else if (ENV_PROVIDER === 'deepseek' && ENV_DS_KEY) {
    payload.deepseek = true;
    payload.deepseek_detail = { deepseek_api_key: ENV_DS_KEY, deepseek_model: ENV_DS_MODEL };
  } else if (ENV_PROVIDER === 'openaicompatible' && ENV_OC_BASE && ENV_OC_KEY && ENV_OC_MODEL) {
    payload.openaicompatible = true;
    payload.openaicompatible_detail = {
      openai_compatible_base_url: ENV_OC_BASE,
      openai_compatible_api_key: ENV_OC_KEY,
      openai_compatible_model: ENV_OC_MODEL
    };
  }

  try {
    await taskStore.submitTask(selectedFile.value, payload);
    // No local remember in server-deploy edition
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

.login-hint {
  margin-top: 0.75rem;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.login-hint {
  margin-top: 0.75rem;
  font-size: 0.8rem;
  color: var(--text-muted);
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

.field-group {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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
