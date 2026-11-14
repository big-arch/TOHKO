(() => {
  document.documentElement.classList.add('portal-js');
  const motionQuery = matchMedia('(prefers-reduced-motion: reduce)');
  window.portalReduceMotion = motionQuery.matches;
  motionQuery.addEventListener('change', (event) => { window.portalReduceMotion = event.matches; });

  const stylesheet = document.createElement('link');
  stylesheet.rel = 'stylesheet';
  stylesheet.href = 'motion.css';
  document.head.appendChild(stylesheet);

  const curve = 'cubic-bezier(0.22,1,0.36,1)';
  const animateIn = (element, delay = 0) => {
    if (window.portalReduceMotion || !element.animate) return;
    element.animate([
      { opacity: 0, transform: 'translateY(32px)' },
      { opacity: 1, transform: 'translateY(0)' }
    ], { duration: 700, delay, easing: curve, fill: 'both' });
  };

  function initRevealAnimations() {
    const items = [...document.querySelectorAll('.portal-reveal')];
    if (!items.length) return;
    if (!('IntersectionObserver' in window)) {
      items.forEach((item) => item.classList.add('visible'));
      return;
    }
    let sequence = 0;
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('visible');
        animateIn(entry.target, Math.min(sequence * 60, 240));
        sequence = (sequence + 1) % 5;
        observer.unobserve(entry.target);
      });
    }, { threshold: .08, rootMargin: '0px 0px -32px' });
    items.forEach((item) => observer.observe(item));
  }

  function initCounters() {
    const counters = [...document.querySelectorAll('[data-brand-count],[data-model-count],[data-photo-count]')];
    if (!counters.length) return;
    const animate = (element) => {
      const target = Number(element.textContent);
      if (!Number.isFinite(target) || window.portalReduceMotion) return;
      const started = performance.now();
      const duration = 1200;
      const tick = (time) => {
        const progress = Math.min(1, (time - started) / duration);
        const eased = 1 - Math.pow(1 - progress, 3);
        element.textContent = Math.round(target * eased);
        if (progress < 1) requestAnimationFrame(tick);
        else element.textContent = target;
      };
      requestAnimationFrame(tick);
    };
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        animate(entry.target);
        observer.unobserve(entry.target);
      });
    }, { threshold: .5 });
    counters.forEach((counter) => observer.observe(counter));
  }

  function initWordReveal() {
    const block = document.querySelector('[data-word-reveal]');
    if (!block) return;
    const parts = block.textContent.trim().split(/\s+/);
    block.textContent = '';
    parts.forEach((part, index) => {
      const word = document.createElement('span');
      word.className = 'portal-word';
      word.textContent = part;
      block.append(word);
      if (index < parts.length - 1) block.append(document.createTextNode(' '));
    });
    const words = [...block.querySelectorAll('.portal-word')];
    let frame = null;
    const update = () => {
      frame = null;
      if (window.portalReduceMotion) {
        words.forEach((word) => word.classList.add('active'));
        return;
      }
      const rect = block.getBoundingClientRect();
      const progress = Math.max(0, Math.min(1, (innerHeight * .82 - rect.top) / (rect.height + innerHeight * .28)));
      const count = Math.ceil(progress * words.length);
      words.forEach((word, index) => word.classList.toggle('active', index < count));
    };
    const request = () => {
      if (frame === null) frame = requestAnimationFrame(update);
    };
    addEventListener('scroll', request, { passive: true });
    addEventListener('resize', request);
    update();
  }

  function initDynamicGridAnimations() {
    ['brand-catalog-grid', 'photo-gallery-grid'].forEach((id) => {
      const grid = document.getElementById(id);
      if (!grid) return;
      const animateChildren = () => {
        [...grid.children].forEach((child, index) => animateIn(child, Math.min(index * 55, 220)));
      };
      animateChildren();
      let queued = false;
      new MutationObserver(() => {
        if (queued) return;
        queued = true;
        requestAnimationFrame(() => {
          queued = false;
          animateChildren();
        });
      }).observe(grid, { childList: true });
    });
  }

  function initHeroParallax() {
    const figure = document.querySelector('.portal-hero-photo');
    const image = figure?.querySelector('img');
    if (!figure || !image || !matchMedia('(pointer:fine)').matches) return;
    let frame = null;
    let point = { x: 0, y: 0 };
    const render = () => {
      frame = null;
      if (!window.portalReduceMotion) image.style.transform = `scale(1.035) translate(${point.x}px,${point.y}px)`;
    };
    figure.addEventListener('pointermove', (event) => {
      const rect = figure.getBoundingClientRect();
      point = { x: ((event.clientX - rect.left) / rect.width - .5) * 12, y: ((event.clientY - rect.top) / rect.height - .5) * 12 };
      if (frame === null) frame = requestAnimationFrame(render);
    });
    figure.addEventListener('pointerleave', () => {
      if (window.portalReduceMotion || !image.animate) return;
      image.animate([
        { transform: getComputedStyle(image).transform },
        { transform: 'scale(1) translate(0,0)' }
      ], { duration: 500, easing: curve, fill: 'forwards' });
    });
  }

  function initScrollProgress() {
    if (!document.querySelector('.portal-brand-content,.portal-brand-prose,#den-lab')) return;
    const bar = document.createElement('div');
    bar.className = 'portal-scroll-progress';
    bar.setAttribute('aria-hidden', 'true');
    document.body.appendChild(bar);
    let frame = null;
    const update = () => {
      frame = null;
      const total = document.documentElement.scrollHeight - innerHeight;
      const progress = total > 0 ? Math.min(1, Math.max(0, scrollY / total)) : 0;
      bar.style.transform = `scaleX(${progress})`;
    };
    const request = () => {
      if (frame === null) frame = requestAnimationFrame(update);
    };
    addEventListener('scroll', request, { passive: true });
    addEventListener('resize', request);
    update();
  }

  initRevealAnimations();
  initCounters();
  initWordReveal();
  initDynamicGridAnimations();
  initHeroParallax();
  initScrollProgress();
})();
