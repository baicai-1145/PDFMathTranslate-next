<template>
  <div class="pdf-viewer" ref="container"></div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue';
import * as pdfjsLib from 'pdfjs-dist';
import 'pdfjs-dist/web/pdf_viewer.css';

pdfjsLib.GlobalWorkerOptions.workerPort = new Worker(
  new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url),
  { type: 'module' }
);

const props = defineProps<{
  url?: string | null;
  data?: Uint8Array | null;
}>();

const container = ref<HTMLDivElement | null>(null);
let cleanupFns: Array<() => void> = [];
let scroller: HTMLDivElement | null = null;
let renderTicket = 0;
const DEBUG_PREVIEW =
  String((import.meta.env as any).VITE_DEBUG_PREVIEW || '').toLowerCase() === 'true' ||
  import.meta.env.DEV;
function log(...args: unknown[]) {
  if (DEBUG_PREVIEW) console.debug('[PdfViewer]', ...args);
}

function cleanup() {
  cleanupFns.forEach((fn) => {
    try {
      fn();
    } catch (error) {
      console.warn('cleanup pdf task failed', error);
    }
  });
  cleanupFns = [];
  if (container.value) {
    container.value.innerHTML = '';
  }
  scroller = null;
}

async function renderPdf() {
  cleanup();
  const ticket = ++renderTicket;
  if (!container.value) return;

  const source =
    props.data && props.data.byteLength
      ? { data: props.data }
      : props.url
        ? { url: props.url, withCredentials: false }
        : null;

  if (!source) return;

  const loadingTask = pdfjsLib.getDocument(source as any);
  cleanupFns.push(() => loadingTask.destroy());

  const pdf = await loadingTask.promise;
  if (ticket !== renderTicket) return; // superseded
  log('loaded pdf', { pages: pdf.numPages, hasData: Boolean((source as any).data), url: (source as any).url });
  const pages = pdf.numPages;

  const root = container.value;
  root.innerHTML = '';

  scroller = document.createElement('div');
  scroller.className = 'pdf-scroller';
  root.appendChild(scroller);
  log('scroller created and appended');

  // Create placeholders to preserve order
  const entries: Array<{ container: HTMLDivElement; canvas: HTMLCanvasElement }> = [];
  for (let n = 1; n <= pages; n += 1) {
    const pageContainer = document.createElement('div');
    pageContainer.className = 'pdf-page';
    const canvas = document.createElement('canvas');
    pageContainer.appendChild(canvas);
    scroller.appendChild(pageContainer);
    entries.push({ container: pageContainer, canvas });
  }

  const CONCURRENCY = Number((import.meta.env as any).VITE_PDF_RENDER_CONCURRENCY || 2);
  let nextIndex = 1;
  const worker = async () => {
    while (true) {
      const pageNumber = nextIndex++;
      if (pageNumber > pages) return;
      if (ticket !== renderTicket || !scroller) return;
      const { container: pageContainer, canvas } = entries[pageNumber - 1];
      const context = canvas.getContext('2d');
      if (!context) continue;
      const page = await pdf.getPage(pageNumber);
      const baseViewport = page.getViewport({ scale: 1 });
      const parentWidth =
        pageContainer.parentElement?.clientWidth || scroller?.clientWidth || (container.value?.clientWidth || 800);
      const safeWidth = Math.max(parentWidth - 24, 200);
      const scale = Math.min(Math.max(safeWidth / baseViewport.width, 0.6), 1.6);
      const viewport = page.getViewport({ scale });
      const outputScale = window.devicePixelRatio || 1;
      canvas.width = Math.floor(viewport.width * outputScale);
      canvas.height = Math.floor(viewport.height * outputScale);
      canvas.style.width = '100%';
      canvas.style.height = 'auto';
      const renderContext = {
        canvasContext: context,
        transform: [outputScale, 0, 0, outputScale, 0, 0],
        viewport,
      } as any;
      const renderTask = page.render(renderContext);
      cleanupFns.push(() => renderTask.cancel());
      try {
        await renderTask.promise;
        log('page rendered', pageNumber);
      } catch (error: any) {
        if (error?.name !== 'RenderingCancelledException') {
          console.warn('PDF render error', error);
        }
      }
      if (ticket !== renderTicket) return;
    }
  };
  const workers: Promise<void>[] = [];
  for (let i = 0; i < Math.max(1, CONCURRENCY); i += 1) {
    workers.push(worker());
  }
  await Promise.all(workers);

  root.dispatchEvent(new CustomEvent('pdf-rendered', { bubbles: true }));
  log('pdf-rendered event dispatched');
}

watch(
  () => [props.url, props.data],
  () => {
    renderPdf().catch((error) => console.warn('render pdf failed', error));
  }
);

onMounted(() => {
  renderPdf().catch((error) => console.warn('render pdf failed', error));
});

onBeforeUnmount(() => {
  cleanup();
});

defineExpose({
  getScroller: () => scroller,
});
</script>

<style scoped>
.pdf-viewer {
  width: 100%;
  height: 100%;
}

.pdf-scroller {
  width: 100%;
  height: 100%;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 0.25rem;
}

.pdf-page {
  background: var(--surface-muted);
  border-radius: 0.75rem;
  padding: 0.75rem;
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.12);
  display: flex;
  justify-content: center;
}

.pdf-page canvas {
  width: 100%;
  height: auto;
  border-radius: 0.5rem;
}
</style>
