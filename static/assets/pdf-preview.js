/* Prévia isolada da página de documentação; não altera o script compartilhado. */
(() => {
  'use strict';
  const dialog = document.querySelector('#pdf-preview');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const $ = selector => dialog.querySelector(selector);
  const title = $('#pdf-title'), status = $('#pdf-status'), stage = $('#pdf-stage');
  const canvas = $('#pdf-canvas'), error = $('#pdf-error'), pager = $('#pdf-page-label');
  const previous = $('#pdf-previous'), next = $('#pdf-next'), zoom = $('#pdf-zoom');
  const closeButton = $('#pdf-close');
  // Versão fixa do pacote Mozilla, via jsDelivr (CDN indicado na documentação).
  // Biblioteca e worker precisam ter exatamente a mesma versão. Sem scripts de PDF.
  const CDN = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/';
  let libraryPromise, loadingTask, pdf, rendering, opener, session = 0, revision = 0;
  let pageNumber = 1, closing = false, resizeTimer, originalOverflow, originalPadding;
  let lastWidth = 0;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  function library() {
    if (!libraryPromise) {
      libraryPromise = import(CDN + 'build/pdf.min.mjs').then(pdfjsLib => {
        pdfjsLib.GlobalWorkerOptions.workerSrc = CDN + 'build/pdf.worker.min.mjs';
        return pdfjsLib;
      }).catch(reason => { libraryPromise = null; throw reason; });
    }
    return libraryPromise;
  }
  function deadline(promise, ms = 25000) {
    let timer;
    return Promise.race([promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error('Tempo de carregamento excedido')), ms);
    })]).finally(() => clearTimeout(timer));
  }
  function controls(busy) {
    previous.disabled = busy || !pdf || pageNumber <= 1;
    next.disabled = busy || !pdf || pageNumber >= pdf.numPages;
    zoom.disabled = busy || !pdf;
  }
  function release() {
    revision++;
    clearTimeout(resizeTimer);
    if (rendering) { rendering.cancel(); rendering = null; }
    // Destroy também interrompe a leitura e encerra o worker após fechar ou falhar.
    const task = loadingTask;
    loadingTask = null; pdf = null;
    if (task) Promise.resolve(task.destroy()).catch(() => {});
    canvas.width = canvas.height = 0;
  }
  function failure(id) {
    if (id !== session || closing || !dialog.open) return;
    release(); controls(true);
    canvas.hidden = true; error.hidden = false;
    status.textContent = 'Prévia indisponível.';
    stage.setAttribute('aria-busy', 'false');
  }
  async function renderPage(id, resetScroll = false) {
    if (!pdf || id !== session || closing) return;
    const currentPDF = pdf, version = ++revision;
    const oldRender = rendering;
    if (oldRender) {
      oldRender.cancel();
      try { await oldRender.promise; } catch (_) { /* Cancelamento esperado. */ }
    }
    if (version !== revision || id !== session) return;
    controls(true); canvas.hidden = true;
    stage.setAttribute('aria-busy', 'true'); status.textContent = 'Renderizando página…';
    try {
      const page = await deadline(currentPDF.getPage(pageNumber));
      if (id !== session || version !== revision) return;
      const base = page.getViewport({ scale: 1 });
      const width = Math.max(100, stage.clientWidth - 32);
      const scale = Math.min(width / base.width, 2) * Number(zoom.value);
      const viewport = page.getViewport({ scale });
      // Um canvas por vez, DPR limitado e teto de pixels para evitar excesso de memória.
      const ratio = Math.min(window.devicePixelRatio || 1, 2,
        Math.sqrt(8000000 / (viewport.width * viewport.height)));
      canvas.width = Math.ceil(viewport.width * ratio);
      canvas.height = Math.ceil(viewport.height * ratio);
      canvas.style.width = viewport.width + 'px';
      canvas.style.height = viewport.height + 'px';
      canvas.setAttribute('aria-label', title.textContent + ', página ' + pageNumber + ' de ' + currentPDF.numPages);
      const task = page.render({ canvasContext: canvas.getContext('2d'), viewport,
        transform: ratio === 1 ? null : [ratio, 0, 0, ratio, 0, 0] });
      rendering = task;
      await deadline(task.promise);
      if (id !== session || version !== revision) return;
      rendering = null; page.cleanup(); canvas.hidden = false;
      pager.textContent = 'Página ' + pageNumber + ' de ' + currentPDF.numPages;
      status.textContent = 'Página ' + pageNumber + ' carregada.';
      stage.setAttribute('aria-busy', 'false'); controls(false);
      if (resetScroll) stage.scrollTo({ top: 0, left: 0, behavior: 'instant' });
    } catch (reason) {
      if (id !== session || version !== revision || reason.name === 'RenderingCancelledException') return;
      failure(id);
    }
  }
  async function open(button, link, name) {
    if (dialog.open || closing) return;
    const id = ++session;
    opener = button; pageNumber = 1; zoom.value = '1';
    title.textContent = name;
    dialog.querySelectorAll('[data-pdf-download]').forEach(a => {
      // Copiar o atributo preserva literalmente o href já publicado no card.
      a.setAttribute('href', link.getAttribute('href'));
    });
    error.hidden = true; canvas.hidden = true;
    pager.textContent = 'Carregando…'; status.textContent = 'Carregando documento…';
    stage.setAttribute('aria-busy', 'true'); controls(true);
    originalOverflow = document.body.style.overflow;
    originalPadding = document.body.style.paddingRight;
    const scrollbar = window.innerWidth - document.documentElement.clientWidth;
    if (scrollbar > 0) document.body.style.paddingRight =
      (parseFloat(getComputedStyle(document.body).paddingRight) + scrollbar) + 'px';
    document.body.style.overflow = 'hidden';
    // showModal torna o restante da página inerte; foco fica contido no dialog.
    dialog.showModal(); lastWidth = stage.clientWidth; closeButton.focus();
    requestAnimationFrame(() => { if (id === session && !closing) dialog.classList.add('is-visible'); });
    try {
      const pdfjsLib = await deadline(library());
      if (id !== session || closing) return;
      const task = pdfjsLib.getDocument({ url: link.href, isEvalSupported: false,
        cMapUrl: CDN + 'cmaps/', cMapPacked: true,
        standardFontDataUrl: CDN + 'standard_fonts/' });
      loadingTask = task;
      task.onPassword = () => failure(id);
      const result = await deadline(task.promise);
      if (id !== session || closing || loadingTask !== task) return;
      pdf = result; await renderPage(id, true);
    } catch (_) { failure(id); }
  }
  function close() {
    if (!dialog.open || closing) return;
    closing = true; session++; release();
    dialog.classList.remove('is-visible');
    // Mantém o modal inerte durante os 300 ms da animação de saída.
    setTimeout(() => {
      dialog.close();
      document.body.style.overflow = originalOverflow;
      document.body.style.paddingRight = originalPadding;
      closing = false;
      if (opener && opener.isConnected) opener.focus({ preventScroll: true });
    }, reducedMotion.matches ? 0 : 300);
  }
  closeButton.addEventListener('click', close);
  dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
  dialog.addEventListener('keydown', event => {
    if (event.key !== 'Tab') return;
    const items = [...dialog.querySelectorAll('a[href],button:not(:disabled),select:not(:disabled),[tabindex="0"]')]
      .filter(el => !el.closest('[hidden]'));
    const first = items[0], last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  previous.addEventListener('click', () => { if (pdf && pageNumber > 1) { pageNumber--; renderPage(session, true); } });
  next.addEventListener('click', () => { if (pdf && pageNumber < pdf.numPages) { pageNumber++; renderPage(session, true); } });
  zoom.addEventListener('change', () => renderPage(session));
  const resize = () => {
    if (!dialog.open || !pdf || closing || Math.abs(stage.clientWidth - lastWidth) < 2) return;
    lastWidth = stage.clientWidth;
    clearTimeout(resizeTimer); resizeTimer = setTimeout(() => renderPage(session), 180);
  };
  if ('ResizeObserver' in window) new ResizeObserver(resize).observe(stage);
  else window.addEventListener('resize', resize);
  document.querySelectorAll('.doc-card').forEach(card => {
    const link = card.querySelector('a[download][href$=".pdf"]');
    const button = card.querySelector('[data-pdf-preview]');
    if (!link || !button) return;
    const name = card.querySelector('h3').textContent.trim();
    button.hidden = false;
    button.setAttribute('aria-label', 'Visualizar ' + name);
    button.addEventListener('click', () => open(button, link, name));
  });
})();
