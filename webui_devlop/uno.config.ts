import { defineConfig, presetUno, presetIcons } from 'unocss';

export default defineConfig({
  theme: {
    colors: {
      primary: {
        DEFAULT: '#0f172a',
        light: '#1f2937'
      },
      secondary: '#94a3b8',
      accent: '#111827',
      muted: '#e2e8f0',
      surface: '#f8fafc'
    },
    fontFamily: {
      sans: 'Inter, "Segoe UI", sans-serif'
    }
  },
  shortcuts: {
    'btn-primary':
      'px-5 py-2 rounded-full font-semibold bg-primary text-white shadow-sm hover:bg-primary-light transition-colors duration-200',
    'btn-secondary':
      'px-4 py-2 rounded-full border border-slate-300 text-slate-600 hover:bg-slate-100 transition-colors duration-200',
    'card':
      'rounded-xl bg-white dark:bg-slate-900 shadow-sm border border-slate-200/60 dark:border-slate-700/60'
  },
  presets: [presetUno(), presetIcons()]
});
