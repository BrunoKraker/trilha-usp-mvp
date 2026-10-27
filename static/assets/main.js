/* =========================================================================
   Trilha USP — comportamento compartilhado
   ========================================================================= */
(function () {
  'use strict';

  /* ---- Menu mobile (drawer) ---- */
  var toggle = document.querySelector('.menu-toggle');
  var nav    = document.querySelector('.main-nav');
  var backdrop = document.querySelector('.drawer-backdrop');

  if (toggle && nav) {
    var open = function () {
      nav.classList.add('is-open');
      toggle.setAttribute('aria-expanded', 'true');
      if (backdrop) backdrop.classList.add('is-open');
    };
    var close = function () {
      nav.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
      if (backdrop) backdrop.classList.remove('is-open');
    };
    toggle.addEventListener('click', function () {
      nav.classList.contains('is-open') ? close() : open();
    });
    if (backdrop) backdrop.addEventListener('click', close);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') close();
    });
  }

  /* ---- Reveal (fade-in suave ao entrar na viewport) ---- */
  var reveals = document.querySelectorAll('.reveal');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (!reduce && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });

    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add('is-visible'); });
  }

  /* ---- Workspace Disciplinas: seleção visual ---- */
  document.querySelectorAll('.disc-item').forEach(function (item) {
    item.addEventListener('click', function () {
      document.querySelectorAll('.disc-item').forEach(function (el) {
        el.classList.remove('selected');
      });
      item.classList.add('selected');
    });
  });

  /* ---- Chips de filtro (Entidades) ---- */
  document.querySelectorAll('.filter-row').forEach(function (row) {
    row.querySelectorAll('.chip').forEach(function (chip) {
      chip.addEventListener('click', function () {
        row.querySelectorAll('.chip').forEach(function (c) {
          c.classList.remove('active');
        });
        chip.classList.add('active');
      });
    });
  });

  /* ---- Ano corrente no rodapé ---- */
  var y = document.querySelectorAll('[data-year]');
  y.forEach(function (el) { el.textContent = new Date().getFullYear(); });
})();

/* Equipe: conteúdo integral, navegação manual e reprodução opcional. */
(function () {
  'use strict';
  var root = document.querySelector('[data-team-carousel]');
  if (!root) return;
  var slides = Array.from(root.querySelectorAll('.member'));
  if (!slides.length) return;
  var current = 0, timer = null;
  var motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var controls = document.createElement('div');
  controls.className = 'team-controls';
  function button(text, label) {
    var el = document.createElement('button');
    el.type = 'button'; el.className = 'btn btn-outline';
    el.textContent = text; el.setAttribute('aria-label', label || text);
    return el;
  }
  var prev = button('Anterior', 'Mostrar integrante anterior');
  var next = button('Próximo', 'Mostrar próximo integrante');
  var play = button('Reproduzir', 'Reproduzir apresentação da equipe');
  play.setAttribute('aria-pressed', 'false');
  var status = document.createElement('span');
  status.className = 'team-status'; status.setAttribute('role', 'status');
  var dots = document.createElement('div'); dots.className = 'team-dots';
  var selectors = slides.map(function (slide, i) {
    slide.id = 'team-member-' + (i + 1);
    slide.setAttribute('role', 'group');
    slide.setAttribute('aria-roledescription', 'slide');
    slide.setAttribute('aria-label', (i + 1) + ' de ' + slides.length);
    var dot = button('', 'Mostrar ' + slide.querySelector('h4').textContent);
    dot.className = 'team-dot'; dot.setAttribute('aria-controls', slide.id);
    dot.addEventListener('click', function () { stop(); show(i); });
    dots.appendChild(dot); return dot;
  });
  function show(index) {
    current = (index + slides.length) % slides.length;
    slides.forEach(function (slide, i) {
      slide.hidden = i !== current;
      slide.classList.toggle('is-entering', i === current);
      selectors[i].setAttribute('aria-current', i === current ? 'true' : 'false');
    });
    status.textContent = (current + 1) + ' de ' + slides.length;
  }
  function stop() {
    clearInterval(timer); timer = null;
    play.textContent = 'Reproduzir'; play.setAttribute('aria-pressed', 'false');
    play.setAttribute('aria-label', 'Reproduzir apresentação da equipe');
    status.setAttribute('aria-live', 'polite');
  }
  prev.addEventListener('click', function () { stop(); show(current - 1); });
  next.addEventListener('click', function () { stop(); show(current + 1); });
  play.addEventListener('click', function () {
    if (timer) { stop(); return; }
    play.textContent = 'Pausar'; play.setAttribute('aria-pressed', 'true');
    play.setAttribute('aria-label', 'Pausar apresentação da equipe');
    status.setAttribute('aria-live', 'off');
    timer = setInterval(function () { show(current + 1); }, 10000);
  });
  root.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault(); stop(); show(current + (e.key === 'ArrowRight' ? 1 : -1));
    }
  });
  root.addEventListener('mouseenter', stop);
  root.addEventListener('focusin', stop);
  document.addEventListener('visibilitychange', function () { if (document.hidden) stop(); });
  motion.addEventListener('change', stop);
  controls.append(prev, status, next, dots, play);
  root.appendChild(controls); root.classList.add('is-carousel'); show(0);
})();
