<template>
  <Teleport to="body">
    <div v-if="auth.showDialog" class="overlay" @click="auth.close">
      <div class="dialog card" @click.stop>
        <header class="header">
          <h3>{{ mode === 'login' ? t('auth.loginTitle') : t('auth.registerTitle') }}</h3>
          <button class="close" @click="auth.close" aria-label="关闭">×</button>
        </header>
        <p class="hint">
          <span v-if="mode === 'login'">{{ t('auth.loginHint') }}</span>
          <span v-else>{{ t('auth.registerHint') }}</span>
        </p>
        <form class="form" @submit.prevent="handleSubmit">
          <label>
            <span>{{ t('auth.username') }}</span>
            <input v-model.trim="username" autocomplete="username" />
          </label>
          <label>
            <span>{{ t('auth.password') }}</span>
            <input v-model="password" type="password" autocomplete="current-password" />
          </label>
          <p v-if="auth.errorMessage" class="error">{{ auth.errorMessage }}</p>
          <button type="submit" class="primary" :disabled="auth.loading">
            {{ auth.loading ? t('auth.loading') : mode === 'login' ? t('auth.loginButton') : t('auth.registerButton') }}
          </button>
        </form>
        <footer class="footer">
          <p>{{ t('auth.guestTip') }}</p>
          <button type="button" class="switch" @click="toggleMode">
            {{ mode === 'login' ? t('auth.gotoRegister') : t('auth.gotoLogin') }}
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useI18n } from '@/i18n';

const auth = useAuthStore();
const { t } = useI18n();

const username = ref('');
const password = ref('');

const mode = computed(() => auth.dialogMode);

watch(
  () => auth.showDialog,
  (visible) => {
    if (visible) {
      username.value = auth.username ?? '';
      password.value = '';
    }
  }
);

function toggleMode() {
  const next = mode.value === 'login' ? 'register' : 'login';
  auth.open(next);
  password.value = '';
}

function handleSubmit() {
  auth
    .handleAuth(mode.value, {
      username: username.value,
      password: password.value
    })
    .catch(() => undefined);
}
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(12, 16, 24, 0.55);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
  box-sizing: border-box;
}

.dialog {
  width: min(420px, 100%);
  padding: 1.8rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background: var(--surface-elevated);
  color: var(--text-primary);
  border-radius: 1rem;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.35);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.close {
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 1.5rem;
  cursor: pointer;
}

.hint {
  margin: 0;
  font-size: 0.9rem;
  color: var(--text-muted);
  line-height: 1.45;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form label {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  font-size: 0.9rem;
}

.form input {
  padding: 0.65rem 0.85rem;
  border-radius: 0.75rem;
  border: 1px solid var(--border-muted);
  background: var(--surface-muted);
  color: var(--text-primary);
}

.error {
  margin: 0;
  color: var(--danger);
  font-size: 0.85rem;
}

.primary {
  border: none;
  border-radius: 0.75rem;
  padding: 0.7rem;
  background: var(--accent);
  color: var(--accent-text);
  font-weight: 600;
  cursor: pointer;
}

.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.switch {
  border: none;
  background: transparent;
  color: var(--accent);
  cursor: pointer;
  font-size: 0.85rem;
}
</style>
