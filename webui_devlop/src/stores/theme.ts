import { defineStore } from 'pinia';
import { ref, watchEffect } from 'vue';

const THEME_STORAGE_KEY = 'pdfmathtranslate-theme';

export const useThemeStore = defineStore('theme', () => {
  const prefersDark =
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-color-scheme: dark)').matches;

  const stored = typeof window !== 'undefined' ? localStorage.getItem(THEME_STORAGE_KEY) : null;

  const isDark = ref(stored ? stored === 'dark' : prefersDark);

  watchEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.dataset.theme = isDark.value ? 'dark' : 'light';
    }
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(THEME_STORAGE_KEY, isDark.value ? 'dark' : 'light');
    }
  });

  const toggleTheme = () => {
    isDark.value = !isDark.value;
  };

  return {
    isDark,
    toggleTheme
  };
});
