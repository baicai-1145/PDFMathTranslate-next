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
    // Keep layout properties only; colors come from CSS variables in theme.css
    'btn-primary':
      'px-5 py-2 rounded-full font-semibold shadow-sm transition-colors duration-200',
    'btn-secondary':
      'px-4 py-2 rounded-full border transition-colors duration-200',
    'card':
      'rounded-xl shadow-sm border'
  },
  presets: [presetUno(), presetIcons()]
});
