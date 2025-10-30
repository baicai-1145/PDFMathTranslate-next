<template>
  <header class="top-bar">
    <div class="brand">
      <div class="brand-mark">{{ t('topbar.title') }}</div>
      <span class="brand-sub">{{ t('topbar.subtitle') }}</span>
    </div>
    <nav class="nav">
      <a class="link" href="https://github.com/PDFMathTranslate/PDFMathTranslate-next" target="_blank" rel="noreferrer">
        {{ t('topbar.github') }}
      </a>
      <a class="link" href="https://pdf2zh-next.com" target="_blank" rel="noreferrer">
        {{ t('topbar.docs') }}
      </a>
    </nav>
    <div class="actions">
      <span class="user">
        {{ isLoggedIn ? `${t('topbar.loggedIn')} · ${displayName}` : t('auth.guestHint') }}
      </span>
      <button class="ghost" @click="handleAuthAction">
        {{ isLoggedIn ? t('auth.switchAccount') : t('auth.loginShort') }}
      </button>
      <button
        v-if="isLoggedIn"
        class="ghost"
        @click="handleLogout"
      >
        {{ t('topbar.logout') }}
      </button>
      <button class="ghost" @click="$emit('toggle-locale')">
        {{ locale === 'zh' ? 'EN' : '中文' }}
      </button>
      <button class="ghost" @click="$emit('toggle-dark')">
        {{ isDark ? t('topbar.light') : t('topbar.dark') }}
      </button>
      <button class="accent" @click="$emit('refresh')">
        {{ t('topbar.refresh') }}
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, toRefs } from 'vue';
import { useI18n } from '@/i18n';
import { useAuthStore } from '@/stores/auth';

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
const auth = useAuthStore();

auth.initialize();

const displayName = computed(() => auth.displayName ?? t('auth.guest'));
const isLoggedIn = computed(() => auth.isLoggedIn);

function handleAuthAction() {
  auth.open();
}

function handleLogout() {
  auth.logout();
}

</script>

<style scoped>
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.25rem;
  padding: 1.5rem 2rem 0;
  width: 100%;
  box-sizing: border-box;
}

.brand {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.brand-mark {
  font-weight: 700;
  font-size: 1.2rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.brand-sub {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--text-muted);
  letter-spacing: 0.18em;
}

.nav {
  display: flex;
  align-items: center;
  gap: 1rem;
  font-size: 0.85rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.link {
  color: var(--text-secondary);
  text-decoration: none;
  transition: color 0.2s ease;
}

.link:hover {
  color: var(--accent);
}

.actions {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  font-size: 0.85rem;
}

.user {
  color: var(--text-muted);
}

.ghost {
  padding: 0.45rem 1.1rem;
  border-radius: 999px;
  border: 1px solid var(--border-muted);
  background: transparent;
  color: var(--text-primary);
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}

.ghost:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--surface-muted);
}

.accent {
  padding: 0.45rem 1.2rem;
  border-radius: 999px;
  border: none;
  background: var(--accent);
  color: var(--accent-text);
  font-weight: 600;
  cursor: pointer;
}

@media (max-width: 1024px) {
  .top-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .actions {
    flex-wrap: wrap;
  }
}
</style>
