const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
window.portalReduceMotion = reducedMotion.matches;
reducedMotion.addEventListener('change', event => { window.portalReduceMotion = event.matches; });
const portal$ = (selector, root = document) => root.querySelector(selector);
const portal$$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const brands = window.BRAND_DATA || [];
const photos = window.PHOTO_DATA || [];
const denLabel = (den) => !den ? 'DEN не заявлен' : den[0] === den[1] ? `${den[0]} DEN` : `${den[0]}–${den[1]} DEN`;
const statusLabel = { active: 'Каталог производителя', archive: 'Архив', retail: 'Розничные источники', limited: 'Часть данных недоступна', medical: 'Медицинская серия' };
const categoryLabel = { women: 'Женская мода', men: 'Мужчины', unisex: 'Унисекс', products: 'Предмет и фактура', leggings: 'Легинсы' };

function portalToast(message) {
  let toast = portal$('#portal-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'portal-toast';
    toast.setAttribute('role', 'status');
    toast.style.cssText = 'position:fixed;right:24px;bottom:24px;z-index:2500;max-width:360px;padding:16px;border-radius:12px;background:#181818;color:#fff;opacity:0;pointer-events:none;transform:translateY(24px);transition:opacity 300ms,transform 500ms;';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.style.opacity = '1';
  toast.style.transform = 'translateY(0)';
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(24px)';
  }, 3000);
}

function initPortalNavigation() {
  const toggle = portal$('[data-nav-toggle]');
  const nav = portal$('.portal-nav');
  if (!toggle || !nav) return;
  const mobile = matchMedia('(max-width: 768px)');
  let open = false;
  const syncInert = () => { nav.inert = mobile.matches && !open; };
  const close = (restoreFocus = false) => {
    open = false;
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', 'Открыть меню');
    nav.classList.remove('open');
    document.body.classList.remove('portal-menu-open');
    syncInert();
    if (restoreFocus) toggle.focus();
  };
  toggle.addEventListener('click', () => {
    open = !open;
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    nav.classList.toggle('open', open);
    document.body.classList.toggle('portal-menu-open', open);
    syncInert();
    if (open) setTimeout(() => portal$('a', nav)?.focus(), 320);
  });
  portal$$('a', nav).forEach((link) => link.addEventListener('click', () => close()));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && open) close(true);
  });
  mobile.addEventListener('change', () => close());
  syncInert();
}

function initPortalReveal() {
  const items = portal$$('.portal-reveal');
  if (!('IntersectionObserver' in window)) {
    items.forEach((item) => item.classList.add('visible'));
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    });
  }, { threshold: .06, rootMargin: '0px 0px -32px' });
  items.forEach((item) => observer.observe(item));
}

function brandLink(item) {
  return `brand.html?brand=${encodeURIComponent(item.slug)}`;
}

function initGlobalCounts() {
  const modelCount = brands.reduce((sum, item) => sum + item.models.length, 0);
  portal$$('[data-brand-count]').forEach((element) => { element.textContent = brands.length; });
  portal$$('[data-model-count]').forEach((element) => { element.textContent = modelCount; });
  portal$$('[data-photo-count]').forEach((element) => { element.textContent = photos.length; });
}

function initFeaturedContent() {
  const featured = portal$('[data-featured-brands]');
  if (featured) {
    const slugs = featured.dataset.featuredBrands.split(',');
    featured.innerHTML = slugs.map((slug) => brands.find((item) => item.slug === slug)).filter(Boolean).map((item) => `
      <article class="portal-brand-tile">
        <div class="portal-page-meta"><span class="portal-chip">${item.country}</span><span class="portal-chip">${item.segment}</span></div>
        <h3>${item.name}</h3>
        <p>${item.summary}</p>
        <a class="portal-text-link" href="${brandLink(item)}">История и ${item.models.length} ${item.models.length === 1 ? 'модель' : 'модели'} <i class="ph ph-arrow-right" aria-hidden="true"></i></a>
      </article>`).join('');
  }
  const homeGallery = portal$('[data-home-gallery]');
  if (homeGallery) {
    const ids = homeGallery.dataset.homeGallery.split(',');
    homeGallery.innerHTML = ids.map((id) => photos.find((item) => item.id === id)).filter(Boolean).map((item) => `
      <a class="portal-story-card" href="lookbook.html#photo-${item.id}">
        <img src="${item.image}" alt="${item.alt}" loading="lazy">
        <div class="portal-story-body"><span class="portal-eyebrow">${categoryLabel[item.category]}</span><h3>${item.title}</h3><span class="portal-text-link">Открыть фотографию <i class="ph ph-arrow-right" aria-hidden="true"></i></span></div>
      </a>`).join('');
  }
  const menBrands = portal$('[data-men-brands]');
  if (menBrands) {
    menBrands.innerHTML = brands.filter((item) => item.segment === 'Мужские' || item.slug === 'medi').map((item) => `
      <article class="portal-brand-tile"><div class="portal-page-meta"><span class="portal-chip">${item.country}</span></div><h3>${item.name}</h3><p>${item.summary}</p><a class="portal-text-link" href="${brandLink(item)}">Открыть карточку <i class="ph ph-arrow-right" aria-hidden="true"></i></a></article>`).join('');
  }
}

function initBrandCatalog() {
  const grid = portal$('#brand-catalog-grid');
  if (!grid) return;
  const search = portal$('#brand-search');
  const segment = portal$('#brand-segment');
  const den = portal$('#brand-den');
  const status = portal$('#brand-status');
  const sort = portal$('#brand-sort');
  const count = portal$('#brand-filter-count');
  const empty = portal$('#brand-empty');
  const tray = portal$('#compare-tray');
  const compareCount = portal$('#compare-count');
  const comparison = portal$('#brand-comparison');
  const compare = new Set();

  const filtered = () => brands.filter((item) => {
    const needle = search.value.trim().toLowerCase();
    const searchable = `${item.name} ${item.country} ${item.summary} ${item.tags.join(' ')} ${item.models.map((entry) => entry.name).join(' ')}`.toLowerCase();
    if (needle && !searchable.includes(needle)) return false;
    if (segment.value !== 'all' && item.segment !== segment.value) return false;
    if (status.value !== 'all' && item.status !== status.value) return false;
    if (den.value !== 'all') {
      const [min, max] = den.value.split('-').map(Number);
      if (!item.models.some((entry) => entry.den && entry.den[1] >= min && entry.den[0] <= max)) return false;
    }
    return true;
  });

  const renderComparison = () => {
    compareCount.textContent = `${compare.size} из 3`;
    tray.classList.toggle('visible', compare.size > 0);
    tray.inert = compare.size === 0;
    if (compare.size < 2) {
      comparison.hidden = true;
      return;
    }
    const selected = [...compare].map((slug) => brands.find((item) => item.slug === slug));
    portal$('#comparison-table').innerHTML = `<thead><tr><th>Критерий</th>${selected.map((item) => `<th><a href="${brandLink(item)}">${item.name}</a></th>`).join('')}</tr></thead><tbody>
      <tr><td>Страна и сегмент</td>${selected.map((item) => `<td>${item.country}<br>${item.segment}</td>`).join('')}</tr>
      <tr><td>Статус данных</td>${selected.map((item) => `<td>${statusLabel[item.status]}</td>`).join('')}</tr>
      <tr><td>Особенности</td>${selected.map((item) => `<td>${item.tags.join(', ') || 'Смотрите карточки моделей'}</td>`).join('')}</tr>
      <tr><td>Проверенные модели</td>${selected.map((item) => `<td>${item.models.length ? `<ul>${item.models.map((entry) => `<li><a target="_blank" rel="noopener" href="${entry.url}">${entry.name}</a> · ${denLabel(entry.den)}</li>`).join('')}</ul>` : 'Нет подтверждённых текущих SKU'}</td>`).join('')}</tr>
    </tbody>`;
    comparison.hidden = false;
    comparison.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const render = () => {
    const list = filtered().sort((a, b) => sort.value === 'models' ? b.models.length - a.models.length : a.name.localeCompare(b.name));
    count.textContent = `Показано ${list.length} из ${brands.length} брендов · ${list.reduce((sum, item) => sum + item.models.length, 0)} моделей`;
    empty.hidden = list.length > 0;
    grid.innerHTML = list.map((item) => `
      <article class="portal-catalog-card">
        <div class="portal-card-top"><span class="portal-chip">${item.country} · ${item.segment}</span><span class="portal-status ${item.status}">${statusLabel[item.status]}</span></div>
        <h2><a href="${brandLink(item)}">${item.name}</a></h2>
        <p>${item.summary}</p>
        ${item.models.length ? `<ul class="portal-model-list">${item.models.slice(0,4).map((entry) => `<li><span>${entry.name}</span><span>${denLabel(entry.den)}</span></li>`).join('')}</ul>` : '<p class="portal-chip">Нет подтверждённых текущих моделей</p>'}
        <div class="portal-card-actions"><a class="portal-text-link" href="${brandLink(item)}">История и каталог <i class="ph ph-arrow-right" aria-hidden="true"></i></a><label class="portal-compare-check"><input type="checkbox" data-compare="${item.slug}" ${compare.has(item.slug) ? 'checked' : ''}> Сравнить</label></div>
      </article>`).join('');
    portal$$('[data-compare]', grid).forEach((checkbox) => checkbox.addEventListener('change', () => {
      const slug = checkbox.dataset.compare;
      if (checkbox.checked && compare.size >= 3) {
        checkbox.checked = false;
        portalToast('Можно сравнить не более трёх брендов');
        return;
      }
      checkbox.checked ? compare.add(slug) : compare.delete(slug);
      renderComparison();
    }));
  };

  [search, segment, den, status, sort].forEach((control) => control.addEventListener(control === search ? 'input' : 'change', render));
  portal$('#brand-reset').addEventListener('click', () => {
    search.value = '';
    segment.value = 'all';
    den.value = 'all';
    status.value = 'all';
    sort.value = 'name';
    render();
  });
  portal$('#compare-open').addEventListener('click', renderComparison);
  portal$('#compare-clear').addEventListener('click', () => {
    compare.clear();
    comparison.hidden = true;
    render();
    renderComparison();
  });
  render();
}

function initBrandDetail() {
  const root = portal$('[data-brand-detail]');
  if (!root) return;
  const slug = new URLSearchParams(location.search).get('brand');
  const item = brands.find((entry) => entry.slug === slug);
  if (!item) { root.innerHTML = '<section class="portal-section"><div class="portal-container"><h1>Бренд не найден</h1><p>Проверьте ссылку или выберите компанию в каталоге.</p><a class="portal-button portal-button-primary" href="brands.html">Открыть каталог</a></div></section>'; document.title = 'Бренд не найден — ТОНКО'; return; }
  document.title = `${item.name}: история компании и модели — ТОНКО`;
  portal$('#brand-title').textContent = item.name;
  portal$('#brand-title-breadcrumb').textContent = item.name;
  portal$('#brand-summary').textContent = item.summary;
  portal$('#brand-country').textContent = item.country;
  portal$('#brand-founded').textContent = item.founded || 'Не подтверждено';
  portal$('#brand-segment-value').textContent = item.segment;
  portal$('#brand-status-value').textContent = statusLabel[item.status];
  portal$('#brand-tags').innerHTML = item.tags.map((tag) => `<span class="portal-chip">${tag}</span>`).join('');
  portal$('#brand-official').href = item.official;
  portal$('#brand-bio').innerHTML = item.bio.map((paragraph) => `<p>${paragraph}</p>`).join('');
  portal$('#brand-milestones').innerHTML = item.milestones.length ? item.milestones.map(([year, text]) => `<div class="portal-timeline-item"><strong>${year}</strong><span>${text}</span></div>`).join('') : '<p>Подробная хронология не опубликована в проверенных источниках. Основные факты приведены в истории выше.</p>';
  portal$('#brand-model-count').textContent = `${item.models.length} ${item.models.length === 1 ? 'модель' : 'моделей'}`;
  portal$('#brand-models').innerHTML = item.models.length ? item.models.map((entry) => `<tr><td><a target="_blank" rel="noopener" href="${entry.url}">${entry.name} <i class="ph ph-arrow-square-out" aria-hidden="true"></i></a></td><td><span class="portal-den">${denLabel(entry.den)}</span></td><td>${entry.use}</td><td>${entry.features}${entry.sourceType === 'retail' ? '<br><span class="portal-chip">Розничное подтверждение</span>' : entry.sourceType === 'archive' ? '<br><span class="portal-chip">Архивный документ</span>' : ''}</td></tr>`).join('') : '<tr><td colspan="4">Текущие модели не подтверждены. Мы не переносим старые названия в актуальный каталог без действующего источника.</td></tr>';
  const related = brands.filter((entry) => entry.segment === item.segment && entry.slug !== item.slug).slice(0,4);
  portal$('#brand-related').innerHTML = related.map((entry) => `<a href="${brandLink(entry)}">${entry.name}</a>`).join('');
}

function initPhotoGallery() {
  const grid = portal$('#photo-gallery-grid');
  if (!grid) return;
  const count = portal$('#photo-gallery-count');
  const lightbox = portal$('#photo-lightbox');
  const dialog = portal$('.portal-lightbox-dialog', lightbox);
  const closeButton = portal$('#photo-lightbox-close');
  let lastFocus = null;
  let closing = false;
  lightbox.setAttribute('aria-hidden', 'true');
  const close = async () => {
    if (closing) return;
    closing = true;
    if (!window.portalReduceMotion && dialog.animate) {
      const animation = dialog.animate([
        { opacity: 1, transform: 'translateY(0) scale(1)' },
        { opacity: 0, transform: 'translateY(24px) scale(.98)' }
      ], { duration: 220, easing: 'cubic-bezier(.22,1,.36,1)', fill: 'forwards' });
      await animation.finished.catch(() => {});
      animation.cancel();
    }
    lightbox.classList.remove('active');
    lightbox.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('portal-modal-open');
    closing = false;
    lastFocus?.focus();
  };
  const open = (item, trigger) => {
    lastFocus = trigger;
    portal$('#lightbox-image').src = item.image;
    portal$('#lightbox-image').alt = item.alt;
    portal$('#lightbox-title').textContent = item.title;
    portal$('#lightbox-caption').textContent = item.caption;
    portal$('#lightbox-author').textContent = item.author;
    portal$('#lightbox-license').textContent = item.license;
    portal$('#lightbox-license').href = item.licenseUrl;
    portal$('#lightbox-source').href = item.source;
    lightbox.classList.add('active');
    lightbox.setAttribute('aria-hidden', 'false');
    document.body.classList.add('portal-modal-open');
    closeButton.focus();
    if (!window.portalReduceMotion && dialog.animate) {
      dialog.animate([
        { opacity: 0, transform: 'translateY(32px) scale(.97)' },
        { opacity: 1, transform: 'translateY(0) scale(1)' }
      ], { duration: 420, easing: 'cubic-bezier(.22,1,.36,1)' });
    }
  };
  const render = (category = 'all') => {
    const list = photos.filter((item) => category === 'all' || item.category === category);
    count.textContent = `Показано ${list.length} из ${photos.length} фотографий`;
    grid.innerHTML = list.map((item) => `<button class="portal-photo-card" type="button" id="photo-${item.id}" data-photo="${item.id}" aria-label="Открыть фотографию: ${item.title}"><img src="${item.image}" alt="${item.alt}" loading="lazy"><span class="portal-photo-copy"><span class="portal-eyebrow">${categoryLabel[item.category]}</span><h2>${item.title}</h2><p>${item.author} · ${item.license}</p></span></button>`).join('');
    portal$$('[data-photo]', grid).forEach((button) => button.addEventListener('click', () => open(photos.find((item) => item.id === button.dataset.photo), button)));
  };
  portal$$('[data-photo-filter]').forEach((button) => button.addEventListener('click', () => {
    portal$$('[data-photo-filter]').forEach((item) => {
      item.classList.toggle('active', item === button);
      item.setAttribute('aria-pressed', String(item === button));
    });
    render(button.dataset.photoFilter);
  }));
  closeButton.addEventListener('click', close);
  lightbox.addEventListener('click', (event) => {
    if (event.target === lightbox) close();
  });
  document.addEventListener('keydown', (event) => {
    if (!lightbox.classList.contains('active')) return;
    if (event.key === 'Escape') close();
    if (event.key === 'Tab') {
      const focusable = portal$$('button, a[href]', dialog).filter((element) => !element.disabled);
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });
  render();
  if (location.hash.startsWith('#photo-')) {
    const target = portal$(location.hash);
    target?.scrollIntoView({ block: 'center' });
  }
}

initPortalNavigation();
initPortalReveal();
initGlobalCounts();
initFeaturedContent();
initBrandCatalog();
initBrandDetail();
initPhotoGallery();

function initGuideLab() {
  const slider = portal$('#den-slider');
  if (slider) {
    const ranges = [
      { max: 15, title: 'Ультрапрозрачные', text: 'Тонкая вуаль для тёплой погоды и естественного вида кожи. Прочность зависит от нити, кроя и обращения.' },
      { max: 40, title: 'На каждый день', text: 'Баланс заметности и покрытия для офиса и прогулок. Финиш может быть матовым, сатиновым или глянцевым.' },
      { max: 70, title: 'Плотные', text: 'Более ровный цвет и меньшая прозрачность. Часто используется мягкая микрофибра.' },
      { max: 100, title: 'Непрозрачные', text: 'Плотная цветная основа для прохладной погоды. Тепло зависит также от состава и плетения.' },
      { max: 150, title: 'Очень плотные', text: 'Вариант для холодного сезона. Для термомоделей ищите начёс, шерсть или прямое назначение производителя.' }
    ];
    const update = () => {
      const value = Number(slider.value);
      const item = ranges.find((entry) => value <= entry.max);
      portal$('#den-value').textContent = value;
      portal$('#den-title').textContent = item.title;
      portal$('#den-description').textContent = item.text;
      portal$('#fabric-layer').style.opacity = String(.03 + value / 190);
    };
    slider.addEventListener('input', update);
    update();
  }
  const sizeForm = portal$('#size-form');
  if (sizeForm) {
    sizeForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const result = portal$('#size-result');
      if (!sizeForm.reportValidity()) {
        result.textContent = 'Проверьте поля: рост от 130 до 210 см и вес от 35 до 180 кг.';
        return;
      }
      const height = Number(portal$('#height').value);
      const weight = Number(portal$('#weight').value);
      const heightSize = [[158,1],[165,2],[175,3],[180,4],[190,5],[210,6]].find(([max]) => height <= max)?.[1] || 6;
      const weightSize = [[55,1],[65,2],[75,3],[90,4],[110,5],[135,6]].find(([max]) => weight <= max)?.[1];
      if (!weightSize) {
        result.textContent = 'Параметры выходят за общую таблицу. Ищите расширенный размерный ряд и сверяйте отдельные мерки.';
        return;
      }
      const labels = ['1 · XS','2 · S','3 · M','4 · L','5 · XL','6 · XXL'];
      result.textContent = `Ориентир: ${labels[Math.max(heightSize, weightSize) - 1]}. Обязательно сверьте результат с таблицей производителя.`;
    });
  }
  const care = portal$('#care-form');
  if (care) {
    const checks = portal$$('input[type="checkbox"]', care);
    const update = () => {
      const done = checks.filter((check) => check.checked).length;
      portal$('#care-progress').textContent = `Готово ${done} из ${checks.length}`;
      try { localStorage.setItem('denie-portal-care', JSON.stringify(checks.filter((check) => check.checked).map((check) => check.value))); } catch {}
    };
    try {
      const saved = JSON.parse(localStorage.getItem('denie-portal-care') || '[]');
      checks.forEach((check) => { check.checked = saved.includes(check.value); });
    } catch {}
    checks.forEach((check) => check.addEventListener('change', update));
    portal$('#care-reset').addEventListener('click', () => {
      checks.forEach((check) => { check.checked = false; });
      update();
    });
    const done = checks.filter((check) => check.checked).length;
    portal$('#care-progress').textContent = `Готово ${done} из ${checks.length}`;
  }
}
initGuideLab();
