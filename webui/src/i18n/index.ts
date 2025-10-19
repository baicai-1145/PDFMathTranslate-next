import { ref, computed, watchEffect } from 'vue';

type Locale = 'zh' | 'en';

const STORAGE_KEY = 'pdfmathtranslate-locale';

const dictionary: Record<Locale, Record<string, string>> = {
  zh: {
    'upload.title': '上传文档',
    'upload.subtitle': '已登录用户的任务会长期保存，欢迎你，',
    'upload.drop': '拖拽或点击上传 PDF / 图片',
    'upload.start': '开始解析',
    'upload.advanced': '高级配置（点击展开）',
    'upload.langFrom': '源语言',
    'upload.langTo': '目标语言',
    'upload.serviceTitle': '翻译服务',
    'upload.siliconflowKey': 'SiliconFlow API 密钥（可选）',
    'upload.rememberConfig': '记住当前配置',
    'task.listTitle': '任务列表',
    'task.empty': '上传任务后将在此显示进度',
    'task.refresh': '刷新',
    'task.statusLabel': '状态',
    'task.createdAt': '创建时间',
    'task.lastUpdated': '最近更新',
    'task.noResult': '尚未生成可下载文件',
    'main.chooseTask': '请选择左侧任务查看详情',
    'main.status': '状态',
    'main.progress': '进度',
    'main.downloadMono': '下载译文',
    'main.downloadDual': '下载双语',
    'main.downloadOriginal': '下载原文',
    'main.inProgress': '任务进行中，请稍候...',
    'main.failed': '任务失败',
    'main.summary': '任务摘要',
    'main.downloads': '下载中心',
    'main.events': '事件记录',
    'preview.title': '结果预览',
    'preview.single': '译文预览',
    'preview.dual': '双栏预览',
    'preview.close': '退出预览',
    'preview.loading': '加载预览中...',
    'preview.prompt': '选择上方按钮查看预览',
    'preview.source': '原文',
    'preview.target': '译文',
    'topbar.title': 'PDFMathTranslate',
    'topbar.subtitle': 'Web Console',
    'topbar.github': 'GitHub',
    'topbar.docs': '文档',
    'topbar.logout': '退出',
    'topbar.dark': '暗色模式',
    'topbar.light': '亮色模式',
    'topbar.refresh': '刷新任务',
    'topbar.loggedIn': '已登录',
    'topbar.user': '访客',
    'topbar.language': '语言',
    'set.lang': '语言'
  },
  en: {
    'upload.title': 'Upload Document',
    'upload.subtitle': 'Your tasks will be kept for a long time, welcome, ',
    'upload.drop': 'Drag or click to upload PDF / Image',
    'upload.start': 'Start Parsing',
    'upload.advanced': 'Advanced Settings (click to expand)',
    'upload.langFrom': 'Source Language',
    'upload.langTo': 'Target Language',
    'upload.serviceTitle': 'Translation Service',
    'upload.siliconflowKey': 'SiliconFlow API Key (optional)',
    'upload.rememberConfig': 'Remember current settings',
    'task.listTitle': 'Task List',
    'task.empty': 'Tasks will appear here once uploaded',
    'task.refresh': 'Refresh',
    'task.statusLabel': 'Status',
    'task.createdAt': 'Created',
    'task.lastUpdated': 'Updated',
    'task.noResult': 'No downloadable files yet',
    'main.chooseTask': 'Select a task on the left to view details',
    'main.status': 'Status',
    'main.progress': 'Progress',
    'main.downloadMono': 'Download Translation',
    'main.downloadDual': 'Download Bilingual',
    'main.downloadOriginal': 'Download Original',
    'main.inProgress': 'Task is running, please wait...',
    'main.failed': 'Task failed',
    'main.summary': 'Summary',
    'main.downloads': 'Downloads',
    'main.events': 'Event Log',
    'preview.title': 'Preview',
    'preview.single': 'Translation Preview',
    'preview.dual': 'Dual Preview',
    'preview.close': 'Close Preview',
    'preview.loading': 'Loading preview...',
    'preview.prompt': 'Use the buttons above to load a preview',
    'preview.source': 'Original',
    'preview.target': 'Translation',
    'topbar.title': 'PDFMathTranslate',
    'topbar.subtitle': 'Web Console',
    'topbar.github': 'GitHub',
    'topbar.docs': 'Docs',
    'topbar.logout': 'Logout',
    'topbar.dark': 'Dark Mode',
    'topbar.light': 'Light Mode',
    'topbar.refresh': 'Refresh Tasks',
    'topbar.loggedIn': 'Logged in',
    'topbar.user': 'visitor',
    'topbar.language': 'Language',
    'set.lang': 'Language'
  }
};

const locale = ref<Locale>(
  (localStorage.getItem(STORAGE_KEY) as Locale | null) ?? 'zh'
);

watchEffect(() => {
  localStorage.setItem(STORAGE_KEY, locale.value);
});

const t = (key: string) => {
  const table = dictionary[locale.value] ?? dictionary.zh;
  return table[key] ?? key;
};

const currentLocale = computed(() => locale.value);

function toggleLocale() {
  locale.value = locale.value === 'zh' ? 'en' : 'zh';
}

export function useI18n() {
  return {
    t,
    locale: currentLocale,
    toggleLocale,
    setLocale(newLocale: Locale) {
      locale.value = newLocale;
    }
  };
}
