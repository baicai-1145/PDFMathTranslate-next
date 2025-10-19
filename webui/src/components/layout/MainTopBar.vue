<template>
  <header class="top-bar card">
    <div class="brand">
      <div class="brand-mark">{{ t('topbar.title') }}</div>
      <span class="brand-sub">{{ t('topbar.subtitle') }}</span>
    </div>
    <nav class="actions">
      <a class="link" href="https://github.com/PDFMathTranslate/PDFMathTranslate-next" target="_blank" rel="noreferrer">
        {{ t('topbar.github') }}
      </a>
      <a class="link" href="https://pdf2zh-next.com" target="_blank" rel="noreferrer">
        {{ t('topbar.docs') }}
      </a>
      <span class="tag">{{ t('topbar.loggedIn') }}: {{ t('topbar.user') }}</span>
      <button class="btn-secondary" @click="$emit('toggle-locale')">
        {{ locale === 'zh' ? 'EN' : '中文' }}
      </button>
      <button class="btn-secondary" @click="$emit('toggle-dark')">
        {{ isDark ? t('topbar.light') : t('topbar.dark') }}
      </button>
      <button class="btn-secondary">
        {{ t('topbar.logout') }}
      </button>
      <button class="btn-primary" @click="$emit('refresh')">
        {{ t('topbar.refresh') }}
      </button>
    </nav>
  </header>
</template>

<script setup lang="ts">
import { useI18n } from '@/i18n';

import { toRefs } from 'vue';

const props = defineProps<{
  isDark: boolean;
  locale: string;
}>();

defineEmits<{
  (e: 'toggle-dark'): void;
  (e: 'refresh'): void;
  (e: 'toggle-locale'): void;
}>();

const { t } = useI18n();
const { locale, isDark } = toRefs(props);

</script>

<style scoped>
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 1.5rem auto 0;
  padding: 1.25rem 2rem;
  max-width: 1400px;
  width: 100%;
  backdrop-filter: blur(12px);
  background: var(--surface-elevated);
}

.brand {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.brand-mark {
  font-weight: 700;
  font-size: 1.15rem;
  letter-spacing: 0.08em;
}

.brand-sub {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--text-muted);
  letter-spacing: 0.2em;
}

.actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.link {
  color: var(--text-secondary);
  font-weight: 500;
  text-decoration: none;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  transition: background 0.2s;
}

.link:hover {
  background: var(--surface-muted);
}

.tag {
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  background: var(--surface-muted);
  color: var(--text-secondary);
  font-size: 0.875rem;
}

@media (max-width: 1024px) {
  .top-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .actions {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}
</style>
