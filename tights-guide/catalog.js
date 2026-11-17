/* Price catalogue. Data is a dated snapshot; the seller remains the price source. */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root && root.document) { root.TONKO_CATALOG_HELPERS = api; api.mount(root); }
})(typeof window === 'object' ? window : null, function () {
  'use strict';
  const PAGE_SIZE = 48;
  const STALE_MS = 48 * 60 * 60 * 1000;
  const DEFAULTS = Object.freeze({q: '', brand: 'all', kind: 'all', gender: 'all', price: 'all', sort: 'brand'});
  const BANDS = Object.freeze({under500: [0, 500], '500-999': [500, 1000], '1000-1999': [1000, 2000], '2000-4999': [2000, 5000], '5000plus': [5000, Infinity]});
  const GENDERS = Object.freeze({women: 'Женские', men: 'Мужские', unisex: 'Унисекс', kids: 'Детские', unknown: 'Не уточнено'});
  const collator = new Intl.Collator('ru', {sensitivity: 'base', numeric: true});
  // Match the static brand directory: Latin brand names first, then Cyrillic.
  const brandCollator = new Intl.Collator('en', {sensitivity: 'base', numeric: true});
  const rubFormat = new Intl.NumberFormat('ru-RU', {maximumFractionDigits: 2});
  const usdFormat = new Intl.NumberFormat('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const rateFormat = new Intl.NumberFormat('ru-RU', {maximumFractionDigits: 4});
  const dayFormat = new Intl.DateTimeFormat('ru-RU', {timeZone: 'Europe/Moscow', day: '2-digit', month: '2-digit', year: 'numeric'});
  const timeFormat = new Intl.DateTimeFormat('ru-RU', {timeZone: 'Europe/Moscow', day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'});
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));
  const normal = value => String(value ?? '').toLocaleLowerCase('ru').replaceAll('ё', 'е').normalize('NFKD').replace(/[\u0300-\u036f]/g, '').trim();
  const validPrice = value => typeof value === 'number' && Number.isFinite(value) && value > 0;
  function timestamp(value) {
    const match = typeof value === 'string' && /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|[+-](\d{2}):(\d{2}))$/.exec(value);
    if (!match || !validDay(match[1]) || Number(match[2]) > 23 || Number(match[3]) > 59 || Number(match[4]) > 59 || Number(match[5] || 0) > 23 || Number(match[6] || 0) > 59) return null;
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  function validDay(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const date = new Date(value + 'T12:00:00Z');
    return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
  }
  function validRate(rate, now = Date.now()) {
    if (!rate || rate.base !== 'USD' || rate.quote !== 'RUB' || !validPrice(rate.rubPerUsd) || !validDay(rate.date)) return null;
    if (rate.date > new Date(now + 3 * 60 * 60 * 1000).toISOString().slice(0, 10)) return null;
    const checked = timestamp(rate.checkedAt);
    if (checked === null || checked > now + 5 * 60 * 1000) return null;
    return rate;
  }
  function freshness(checkedAt, now = Date.now()) {
    const checked = timestamp(checkedAt);
    if (checked === null || checked > now + 5 * 60 * 1000) return 'unknown';
    return now - checked > STALE_MS ? 'stale' : 'fresh';
  }
  function dateText(value, full = false) {
    const parsed = timestamp(value);
    return parsed === null ? 'дата не указана' : (full ? timeFormat : dayFormat).format(parsed) + (full ? ' МСК' : '');
  }
  function effectiveDate(value) {
    return validDay(value) ? dayFormat.format(new Date(value + 'T12:00:00Z')) : 'дата не указана';
  }
  function priceText(item, rate, now = Date.now()) {
    if (!validPrice(item.priceRub)) return {rub: 'Цена не указана', usd: ''};
    const usableRate = validRate(rate, now);
    const from = item.priceFrom ? 'от ' : '';
    return {rub: from + rubFormat.format(item.priceRub) + ' ₽', usd: usableRate ? '≈ ' + (item.priceFrom ? 'от ' : '') + '$' + usdFormat.format(item.priceRub / usableRate.rubPerUsd) : ''};
  }
  function priceBand(item, band) {
    if (band === 'all') return true;
    if (band === 'unknown') return !validPrice(item.priceRub);
    const range = BANDS[band];
    return Boolean(range && validPrice(item.priceRub) && item.priceRub >= range[0] && item.priceRub < range[1]);
  }
  function compareItems(a, b, sort = 'brand') {
    if (sort === 'price-asc' || sort === 'price-desc') {
      const aKnown = validPrice(a.priceRub), bKnown = validPrice(b.priceRub);
      if (aKnown !== bKnown) return aKnown ? -1 : 1;
      if (aKnown && a.priceRub !== b.priceRub) return (a.priceRub - b.priceRub) * (sort === 'price-desc' ? -1 : 1);
    }
    return brandCollator.compare(a.brand || '', b.brand || '') || collator.compare(a.model || a.title || '', b.model || b.title || '') || collator.compare(a.id || '', b.id || '');
  }
  function selectItems(rows, state) {
    const tokens = normal(state.q).split(/\s+/).filter(Boolean);
    return rows.filter(item => {
      if (state.brand !== 'all' && item.brand !== state.brand) return false;
      if (state.kind !== 'all' && item.productKind !== state.kind) return false;
      if (state.gender !== 'all' && (item.gender || 'unknown') !== state.gender) return false;
      if (!priceBand(item, state.price)) return false;
      const haystack = normal([item.brand, item.model, item.title, item.productKind, item.den == null ? '' : item.den + ' DEN', ...(item.categories || []).map(c => c.name || '')].join(' '));
      return tokens.every(token => haystack.includes(token));
    }).sort((a, b) => compareItems(a, b, state.sort));
  }
  function readState(search, rows) {
    const params = new URLSearchParams(search);
    const state = {...DEFAULTS, q: (params.get('q') || '').trim().slice(0, 200)};
    const choices = {brand: new Set(rows.map(r => r.brand)), kind: new Set(rows.map(r => r.productKind)), gender: new Set(rows.map(r => r.gender || 'unknown')), price: new Set([...Object.keys(BANDS), 'unknown']), sort: new Set(['brand', 'price-asc', 'price-desc'])};
    for (const [key, allowed] of Object.entries(choices)) if (allowed.has(params.get(key))) state[key] = params.get(key);
    return state;
  }
  function stateQuery(state, product = '') {
    const params = new URLSearchParams();
    for (const key of Object.keys(DEFAULTS)) {
      const value = String(state[key] ?? DEFAULTS[key]).trim();
      if (value && value !== DEFAULTS[key]) params.set(key, value);
    }
    if (product) params.set('product', product);
    return params.size ? '?' + params.toString() : '';
  }
  function httpsUrl(value) {
    try { const url = new URL(value); return url.protocol === 'https:' && url.hostname ? url.href : ''; } catch (_) { return ''; }
  }
  function imagePath(value) {
    return typeof value === 'string' && /^assets\/catalog\/[a-zA-Z0-9_./%-]+$/.test(value) && !value.includes('..') ? value : '';
  }
  function checkedText(item, now = Date.now()) {
    const state = freshness(item.checkedAt, now);
    if (state === 'unknown') return 'Дата проверки не указана';
    return (validPrice(item.priceRub) ? 'Цена проверена ' : 'Проверено ') + dateText(item.checkedAt) + (state === 'stale' ? ' · требует обновления' : '');
  }
  function cardMarkup(item, rate, state, now = Date.now()) {
    const image = imagePath(item.thumbnail) || imagePath(item.image);
    const price = priceText(item, rate, now);
    const source = httpsUrl(item.source);
    const picture = image ? `<img src="${esc(image)}" alt="${esc(item.title)} — каталожное изображение" width="${Number(item.width) || 480}" height="${Number(item.height) || 640}" loading="lazy" decoding="async">` : '<span class="catalog-no-image">Фото пока недоступно</span>';
    const facts = [item.productKind, item.den == null ? '' : item.den + ' DEN'].filter(Boolean).join(' · ');
    return `<article class="catalog-card" data-id="${esc(item.id)}"><a class="catalog-open" data-product="${esc(item.id)}" href="${esc(stateQuery(state, item.id))}" aria-label="Подробнее: ${esc(item.title)}"><span class="catalog-image">${picture}<span class="catalog-image-open" aria-hidden="true">↗</span></span><span class="catalog-brand">${esc(item.brand)}</span><h3>${esc(item.model || item.title)}</h3></a><p class="catalog-card-facts">${esc(facts)}</p><p class="catalog-price${validPrice(item.priceRub) ? '' : ' is-unknown'}"><strong>${esc(price.rub)}</strong>${price.usd ? `<span>${esc(price.usd)}</span>` : ''}</p><p class="catalog-checked${freshness(item.checkedAt, now) === 'stale' ? ' is-stale' : ''}">${esc(checkedText(item, now))}</p>${item.availability === 'out_of_stock' ? '<p class="catalog-availability">Нет в наличии</p>' : ''}${source ? `<a class="catalog-seller" href="${esc(source)}" target="_blank" rel="noopener noreferrer">У продавца <span aria-hidden="true">↗</span><span class="catalog-sr-only"> — ${esc(item.title)}</span></a>` : ''}</article>`;
  }
  function rateMarkup(rate, now = Date.now()) {
    const usable = validRate(rate, now);
    if (!usable) return '<span>Курс USD пока недоступен. Цены показаны в рублях.</span>';
    const source = httpsUrl(rate.source);
    const label = esc(rate.sourceName || 'Банк России');
    return `${source ? `<a href="${esc(source)}" target="_blank" rel="noopener noreferrer">${label} ↗</a>` : label}: 1 USD = ${esc(rateFormat.format(rate.rubPerUsd))} ₽. Действует с ${effectiveDate(rate.date)}; проверен ${dateText(rate.checkedAt)}${freshness(rate.checkedAt, now) === 'stale' ? ' · требует обновления' : ''}.`;
  }
  function mount(win) {
    const doc = win.document, $ = id => doc.getElementById(id);
    if (!$('catalog-grid')) return;
    const data = win.TONKO_CATALOG;
    if (!data || !Array.isArray(data.items)) {
      $('catalog-runtime-note').hidden = false;
      $('catalog-runtime-note').textContent = 'Показана сохранённая подборка. Поиск временно недоступен.';
      return;
    }
    const rows = data.items, rate = win.TONKO_EXCHANGE_RATE;
    const byId = new Map(rows.map(row => [row.id, row]));
    let state = readState(win.location.search, rows), limit = PAGE_SIZE, shown = [], opener = null, activeProduct = '', priorOverflow = '';
    const dialog = $('catalog-dialog');
    const controls = {q: $('catalog-query'), brand: $('catalog-brand'), kind: $('catalog-kind'), gender: $('catalog-gender'), price: $('catalog-price'), sort: $('catalog-sort')};
    $('catalog-tools').hidden = false;
    $('catalog-actions').hidden = false;
    $('catalog-rate').innerHTML = rateMarkup(rate);
    $('catalog-directory').open = win.matchMedia('(min-width: 901px)').matches;
    function syncControls() { for (const [key, control] of Object.entries(controls)) control.value = state[key]; }
    function syncUrl(product = activeProduct, push = false) {
      const next = win.location.pathname + stateQuery(state, product) + win.location.hash;
      if (next !== win.location.pathname + win.location.search + win.location.hash) win.history[push ? 'pushState' : 'replaceState'](null, '', next);
    }
    function render() {
      shown = selectItems(rows, state);
      const slice = shown.slice(0, limit);
      $('catalog-grid').innerHTML = slice.map(item => cardMarkup(item, rate, state)).join('');
      $('catalog-count').textContent = `Найдено ${shown.length} из ${rows.length} · показано ${slice.length}`;
      $('catalog-empty').hidden = Boolean(shown.length);
      $('catalog-more').hidden = shown.length <= limit;
      $('catalog-more').textContent = `Показать ещё ${Math.min(PAGE_SIZE, Math.max(0, shown.length - limit))}`;
      $('catalog-visible-note').textContent = shown.length > limit ? 'Товары отсортированы во всей выбранной подборке.' : '';
      for (const link of doc.querySelectorAll('[data-catalog-brand]')) {
        const brand = link.dataset.catalogBrand;
        if (brand === state.brand) link.setAttribute('aria-current', 'true'); else link.removeAttribute('aria-current');
        link.href = stateQuery({...state, brand}) || win.location.pathname;
      }
    }
    function change(push = false) {
      const params = new URLSearchParams();
      for (const [key, control] of Object.entries(controls)) params.set(key, control.value);
      state = readState(params, rows); limit = PAGE_SIZE; syncControls(); syncUrl('', push); render();
    }
    function reset() { state = {...DEFAULTS}; limit = PAGE_SIZE; syncControls(); syncUrl(''); render(); controls.q.focus(); }
    function photoList(item) {
      const main = imagePath(item.image);
      const photos = main ? [{src: main, thumb: imagePath(item.thumbnail) || main, alt: item.title}] : [];
      for (const photo of Array.isArray(item.photos) ? item.photos : []) {
        const src = imagePath(typeof photo === 'string' ? photo : photo.src || photo.image);
        if (src && !photos.some(p => p.src === src)) photos.push({src, thumb: imagePath(photo.thumb || photo.thumbnail) || src, alt: photo.alt || item.title});
      }
      return photos;
    }
    function displayPhoto(photo) {
      const image = $('catalog-full'); image.src = photo.src; image.alt = photo.alt + ' — каталожное изображение';
      for (const button of $('catalog-photos').querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.image === photo.src));
    }
    function openProduct(id, trigger = null, updateUrl = true) {
      const item = byId.get(id); if (!item) return;
      if (!dialog.open) { opener = trigger || doc.activeElement; priorOverflow = doc.documentElement.style.overflow; }
      activeProduct = id;
      $('catalog-dialog-brand').textContent = item.brand;
      $('catalog-title').textContent = item.title;
      const price = priceText(item, rate);
      $('catalog-detail-price').innerHTML = `<strong>${esc(price.rub)}</strong>${price.usd ? `<span>${esc(price.usd)}</span>` : ''}`;
      $('catalog-detail-price').classList.toggle('is-unknown', !validPrice(item.priceRub));
      $('catalog-detail-checked').textContent = timestamp(item.checkedAt) === null ? 'Дата проверки не указана.' : `${validPrice(item.priceRub) ? 'Цена проверена' : 'Карточка проверена'} ${dateText(item.checkedAt, true)}.${freshness(item.checkedAt) === 'stale' ? ' Требует обновления.' : ''}`;
      $('catalog-description').textContent = item.description || '';
      $('catalog-description').hidden = !item.description;
      const facts = [['Изделие', item.productKind || 'Не уточнено'], ['Категория', GENDERS[item.gender] || GENDERS.unknown], ['Плотность', item.den == null ? 'Не указана' : item.den + ' DEN'], ['Наличие у источника', {in_stock: 'В наличии', out_of_stock: 'Нет в наличии', unknown: 'Не уточнено'}[item.availability] || 'Не уточнено']];
      $('catalog-facts').innerHTML = facts.map(([key, value]) => `<div><dt>${esc(key)}</dt><dd>${esc(value)}</dd></div>`).join('');
      $('catalog-detail-rate').innerHTML = rateMarkup(rate);
      const source = httpsUrl(item.source);
      $('catalog-source').hidden = !source;
      if (source) $('catalog-source').href = source; else $('catalog-source').removeAttribute('href');
      $('catalog-source-name').textContent = item.sourceName || data.source?.name || 'Источник';
      $('catalog-package').hidden = !item.packageId;
      if (item.packageId) $('catalog-package').href = 'packaging.html?pack=' + encodeURIComponent(item.packageId);
      const photos = photoList(item);
      $('catalog-full').hidden = !photos.length;
      $('catalog-photo-empty').hidden = Boolean(photos.length);
      $('catalog-photos').hidden = photos.length < 2;
      $('catalog-photos').innerHTML = photos.map((photo, index) => `<button type="button" data-image="${esc(photo.src)}" aria-label="Фото ${index + 1}: ${esc(item.title)}" aria-pressed="${index === 0}"><img src="${esc(photo.thumb)}" alt="" loading="lazy"></button>`).join('');
      if (photos.length) displayPhoto(photos[0]); else $('catalog-full').removeAttribute('src');
      if (!dialog.open) dialog.showModal();
      dialog.scrollTop = 0; doc.documentElement.style.overflow = 'hidden';
      if (updateUrl) syncUrl(id);
    }
    function restoreFocus() {
      doc.documentElement.style.overflow = priorOverflow;
      const closedId = activeProduct; activeProduct = '';
      syncUrl('');
      if (opener?.isConnected && opener !== doc.body) opener.focus({preventScroll: true});
      else {
        const target = [...$('catalog-grid').querySelectorAll('[data-product]')].find(el => el.dataset.product === closedId);
        (target || controls.q).focus({preventScroll: true});
      }
    }
    $('catalog-tools').addEventListener('submit', event => { event.preventDefault(); change(); });
    let searchTimer;
    controls.q.addEventListener('input', () => { win.clearTimeout(searchTimer); searchTimer = win.setTimeout(() => change(), 120); });
    for (const [key, control] of Object.entries(controls)) if (key !== 'q') control.addEventListener('change', () => { win.clearTimeout(searchTimer); change(); });
    $('catalog-reset').addEventListener('click', reset); $('catalog-empty-reset').addEventListener('click', reset);
    $('catalog-brand-links').addEventListener('click', event => {
      const link = event.target.closest('[data-catalog-brand]'); if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault(); state.brand = link.dataset.catalogBrand; limit = PAGE_SIZE; syncControls(); syncUrl(''); render();
      if (win.matchMedia('(max-width: 900px)').matches) { $('catalog-directory').open = false; $('catalog-collection').scrollIntoView({block: 'start'}); }
    });
    $('catalog-grid').addEventListener('click', event => {
      const link = event.target.closest('[data-product]'); if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault(); openProduct(link.dataset.product, link);
    });
    $('catalog-more').addEventListener('click', () => {
      const oldLimit = limit; limit += PAGE_SIZE; render();
      $('catalog-grid').querySelectorAll('[data-product]')[oldLimit]?.focus({preventScroll: true});
    });
    $('catalog-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', restoreFocus);
    dialog.addEventListener('click', event => { if (event.target === dialog) { const rect = dialog.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close(); } });
    dialog.addEventListener('keydown', event => {
      if (event.key !== 'Tab') return;
      const focusable = [...dialog.querySelectorAll('button:not([disabled]),a[href]')].filter(el => el.getClientRects().length);
      const first = focusable[0], last = focusable.at(-1);
      if (event.shiftKey && doc.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && doc.activeElement === last) { event.preventDefault(); first?.focus(); }
    });
    $('catalog-photos').addEventListener('click', event => { const button = event.target.closest('[data-image]'); if (button) displayPhoto({src: button.dataset.image, alt: byId.get(activeProduct)?.title || ''}); });
    $('catalog-copy').addEventListener('click', async () => {
      try { await win.navigator.clipboard.writeText(win.location.href); $('catalog-share-status').textContent = 'Ссылка на подборку скопирована.'; }
      catch (_) { $('catalog-share-status').textContent = 'Ссылка на подборку находится в адресной строке.'; }
    });
    win.addEventListener('popstate', () => {
      const product = new URLSearchParams(win.location.search).get('product');
      state = readState(win.location.search, rows); limit = PAGE_SIZE; syncControls(); render();
      if (product && byId.has(product)) openProduct(product, null, false);
      else if (dialog.open) dialog.close();
    });
    syncControls(); render();
    const deepProduct = new URLSearchParams(win.location.search).get('product');
    if (deepProduct && byId.has(deepProduct)) openProduct(deepProduct, null, false);
    else syncUrl('');
  }
  return {PAGE_SIZE, STALE_MS, DEFAULTS, BANDS, GENDERS, validPrice, validDay, validRate, freshness, priceText, priceBand, compareItems, selectItems, readState, stateQuery, cardMarkup, rateMarkup, mount};
});
