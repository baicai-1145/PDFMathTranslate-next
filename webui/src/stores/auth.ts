import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { apiClient, getProfile, login, register } from '@/services/api';
import type { UserProfile } from '@/types/user';

type AuthMode = 'login' | 'register';

const TOKEN_KEY = 'pdfmathtranslate-token';
const USERNAME_KEY = 'pdfmathtranslate-username';
const DISPLAY_KEY = 'pdfmathtranslate-display-name';

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY));
  const username = ref<string | null>(localStorage.getItem(USERNAME_KEY));
  const displayName = ref<string | null>(localStorage.getItem(DISPLAY_KEY));
  const showDialog = ref(false);
  const dialogMode = ref<AuthMode>('login');
  const loading = ref(false);
  const errorMessage = ref<string | null>(null);
  const initialized = ref(false);

  function applyToken(value: string | null) {
    if (value) {
      apiClient.defaults.headers.common.Authorization = `Bearer ${value}`;
    } else {
      delete apiClient.defaults.headers.common.Authorization;
    }
  }

  applyToken(token.value);

  const isLoggedIn = computed(() => Boolean(token.value));

  async function initialize() {
    if (initialized.value) return;
    initialized.value = true;
    if (!token.value) {
      applyToken(null);
      return;
    }
    try {
      const profile = await getProfile(token.value);
      applyProfile(profile, token.value);
    } catch (error) {
      console.warn('Failed to restore session', error);
      clearSession();
    }
  }

  function open(mode: AuthMode = 'login') {
    dialogMode.value = mode;
    showDialog.value = true;
    errorMessage.value = null;
  }

  function close() {
    showDialog.value = false;
    errorMessage.value = null;
  }

  function requireLogin(message?: string) {
    errorMessage.value = message ?? null;
    dialogMode.value = 'login';
    showDialog.value = true;
  }

  function clearSession() {
    token.value = null;
    username.value = null;
    displayName.value = null;
    applyToken(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
    localStorage.removeItem(DISPLAY_KEY);
  }

  function applyProfile(profile: UserProfile, authToken: string) {
    token.value = authToken;
    username.value = profile.username;
    displayName.value = profile.display_name ?? profile.username;
    localStorage.setItem(TOKEN_KEY, authToken);
    localStorage.setItem(USERNAME_KEY, username.value);
    localStorage.setItem(DISPLAY_KEY, displayName.value ?? '');
    applyToken(authToken);
  }

  async function handleAuth(action: AuthMode, creds: { username: string; password: string }) {
    loading.value = true;
    errorMessage.value = null;
    try {
      const trimmed = creds.username.trim();
      if (!trimmed) {
        throw new Error('用户名不能为空');
      }
      if (creds.password.length < 6) {
        throw new Error('密码至少 6 个字符');
      }
      const response =
        action === 'login'
          ? await login(trimmed, creds.password)
          : await register(trimmed, creds.password);
      applyProfile(response.profile, response.token);
      close();
    } catch (error: any) {
      const message =
        error?.response?.data?.detail ||
        error?.message ||
        (action === 'login' ? '登录失败，请重试。' : '注册失败，请重试。');
      errorMessage.value = message;
      throw error;
    } finally {
      loading.value = false;
    }
  }

  function logout() {
    clearSession();
  }

  return {
    token,
    username,
    displayName,
    isLoggedIn,
    showDialog,
    dialogMode,
    loading,
    errorMessage,
    initialize,
    open,
    close,
    requireLogin,
    handleAuth,
    logout
  };
});
