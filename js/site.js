/* glebsfilm — site.js
 * - Fade gallery frames in on viewport intersection
 * - Mobile menu open/close + auto-close on link tap
 * - Hero-aware navbar (transparent over hero, solid after)
 * - Lightbox: click a photo for fullscreen view with arrow-key nav
 */

(function () {
  'use strict';

  // ---------- Frame fade-in ----------
  const frames = document.querySelectorAll('.frame');
  if ('IntersectionObserver' in window && frames.length) {
    const io = new IntersectionObserver((entries, obs) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          obs.unobserve(e.target);
        }
      });
    }, { rootMargin: '120px 0px', threshold: 0.05 });
    frames.forEach(f => io.observe(f));
  } else {
    frames.forEach(f => f.classList.add('in'));
  }

  // ---------- Mobile menu ----------
  const toggle = document.querySelector('.site-nav__toggle');
  const links  = document.querySelector('.site-nav__links');
  if (toggle && links) {
    toggle.addEventListener('click', () => {
      const open = links.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    links.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => {
        links.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  // ---------- Hero-aware navbar ----------
  const nav  = document.querySelector('.site-nav');
  const hero = document.querySelector('.hero');
  if (nav && hero) {
    nav.classList.add('site-nav--on-hero');
    const heroIo = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) nav.classList.add('site-nav--on-hero');
        else                  nav.classList.remove('site-nav--on-hero');
      });
    }, { threshold: 0, rootMargin: '-80px 0px 0px 0px' });
    heroIo.observe(hero);
  }

  // ---------- Lightbox ----------
  initLightbox();

  function initLightbox() {
    const galleryFrames = document.querySelectorAll('.gallery .frame');
    if (!galleryFrames.length) return;

    // Collect photos
    const photos = Array.from(galleryFrames).map(f => {
      const img = f.querySelector('img');
      const src = f.querySelector('source');
      const idx = f.querySelector('.frame__index');
      const meta = f.querySelector('.frame__meta');
      // Pull the largest available image — use the 1600w if present, else current src.
      let large = img ? (img.dataset.large || img.src) : '';
      // Convert -960.webp / -1600.jpg → preferred large
      large = large.replace(/-960\.(webp|jpg)$/, '-1600.$1');
      // Prefer webp if a source provided one
      if (src && src.srcset) {
        const m = src.srcset.match(/(\S*-1600\.webp)/);
        if (m) large = new URL(m[1], document.baseURI).href;
      }
      return {
        src:   large,
        alt:   img ? img.alt : '',
        index: idx  ? idx.textContent.trim() : '',
        meta:  meta ? meta.textContent.trim() : '',
      };
    });

    // Build DOM
    const root = document.createElement('div');
    root.className = 'lightbox';
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-label', 'Photo viewer');
    root.hidden = true;
    root.innerHTML = `
      <button class="lightbox__close" type="button" aria-label="Close (Esc)">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><line x1="4" y1="4" x2="20" y2="20"/><line x1="20" y1="4" x2="4" y2="20"/></svg>
      </button>
      <button class="lightbox__prev" type="button" aria-label="Previous (←)">
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"><polyline points="14 6 8 12 14 18"/></svg>
      </button>
      <button class="lightbox__next" type="button" aria-label="Next (→)">
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"><polyline points="10 6 16 12 10 18"/></svg>
      </button>
      <div class="lightbox__viewport">
        <img class="lightbox__img" alt="">
      </div>
      <div class="lightbox__caption">
        <span class="lightbox__index"></span>
        <span class="lightbox__meta"></span>
        <span class="lightbox__count"></span>
      </div>
    `;
    document.body.appendChild(root);

    const img      = root.querySelector('.lightbox__img');
    const indexEl  = root.querySelector('.lightbox__index');
    const metaEl   = root.querySelector('.lightbox__meta');
    const countEl  = root.querySelector('.lightbox__count');
    let current = -1;

    function open(i) {
      current = i;
      update();
      root.hidden = false;
      // next frame, then add class — triggers fade-in
      requestAnimationFrame(() => root.classList.add('open'));
      document.body.classList.add('lightbox-open');
    }

    function close() {
      root.classList.remove('open');
      document.body.classList.remove('lightbox-open');
      // wait for fade
      setTimeout(() => { root.hidden = true; }, 260);
    }

    function go(delta) {
      current = (current + delta + photos.length) % photos.length;
      update();
    }

    function preload(i) {
      const p = photos[(i + photos.length) % photos.length];
      if (!p) return;
      const im = new Image();
      im.src = p.src;
    }

    function update() {
      const p = photos[current];
      root.classList.add('loading');
      const next = new Image();
      next.onload = () => {
        img.src = p.src;
        img.alt = p.alt;
        root.classList.remove('loading');
      };
      next.onerror = () => root.classList.remove('loading');
      next.src = p.src;
      indexEl.textContent = p.index;
      metaEl.textContent  = p.meta;
      countEl.textContent = `${current + 1} / ${photos.length}`;
      // Preload neighbours
      preload(current + 1);
      preload(current - 1);
    }

    // Bind controls
    root.querySelector('.lightbox__close').addEventListener('click', close);
    root.querySelector('.lightbox__prev').addEventListener('click',  () => go(-1));
    root.querySelector('.lightbox__next').addEventListener('click',  () => go(1));
    root.addEventListener('click', (e) => {
      // Click on the dim backdrop (not on the photo or buttons) closes
      if (e.target === root || e.target.classList.contains('lightbox__viewport')) close();
    });

    // Frame click handlers
    galleryFrames.forEach((f, i) => {
      f.addEventListener('click', (e) => {
        e.preventDefault();
        open(i);
      });
    });

    // Keyboard
    document.addEventListener('keydown', (e) => {
      if (root.hidden) return;
      if (e.key === 'Escape')     close();
      if (e.key === 'ArrowLeft')  go(-1);
      if (e.key === 'ArrowRight') go(1);
    });

    // Touch swipe (basic, horizontal only)
    let startX = null;
    root.addEventListener('touchstart', (e) => { startX = e.touches[0].clientX; }, { passive: true });
    root.addEventListener('touchend',   (e) => {
      if (startX == null) return;
      const dx = e.changedTouches[0].clientX - startX;
      if (Math.abs(dx) > 50) go(dx < 0 ? 1 : -1);
      startX = null;
    });
  }
})();
