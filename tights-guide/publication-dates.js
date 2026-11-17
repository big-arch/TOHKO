/* Publication dates are independent of source checks, imports and reading history. */
(() => {
  'use strict';
  const WEEK = 7 * 24 * 60 * 60 * 1000;
  const format = new Intl.DateTimeFormat('ru-RU', {day:'numeric', month:'long', year:'numeric', timeZone:'UTC'});
  const pattern = /^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2}))?$/;
  function timestamp(value) {
    if (typeof value !== 'string' || !pattern.test(value)) return null;
    // Date.parse normalizes e.g. February 30; an unknown date must stay unknown.
    const calendar = value.slice(0, 10), day = Date.parse(calendar), clock = value.match(/T(\d{2}):(\d{2})(?::(\d{2}))?/);
    if (Number(calendar.slice(0, 4)) < 1 || (clock && (+clock[1] > 23 || +clock[2] > 59 || +clock[3] > 59))) return null;
    if (!Number.isFinite(day) || new Date(day).toISOString().slice(0, 10) !== calendar) return null;
    const stamp = Date.parse(value);
    return Number.isFinite(stamp) ? stamp : null;
  }
  function compareNewest(a, b) {
    const first = timestamp(a), second = timestamp(b);
    if (first === null) return second === null ? 0 : 1;
    return second === null ? -1 : second - first;
  }
  function isNew(value, now = Date.now()) {
    const stamp = timestamp(value), age = now - stamp;
    return stamp !== null && age >= 0 && age < WEEK;
  }
  function refresh(root = document, now = Date.now()) {
    root.querySelectorAll('[data-publication-date]').forEach(meta => {
      const badge = meta.querySelector('[data-publication-new]');
      if (badge) badge.hidden = !isNew(meta.dataset.publicationDate, now);
    });
  }
  function create(value) {
    const meta = document.createElement('span'); meta.className = 'publication-meta';
    const stamp = timestamp(value); meta.dataset.publicationDate = stamp === null ? '' : value;
    if (stamp === null) {
      const unknown = document.createElement('span'); unknown.className = 'publication-undated';
      unknown.textContent = 'Дата публикации не указана'; meta.append(unknown); return meta;
    }
    const text = document.createElement('span'), time = document.createElement('time');
    time.dateTime = value; time.textContent = format.format(new Date(stamp));
    time.setAttribute('aria-label', `Дата публикации: ${time.textContent}`);
    text.append('Опубликовано ', time);
    const badge = document.createElement('span'); badge.className = 'publication-new';
    badge.dataset.publicationNew = ''; badge.textContent = 'Новое';
    badge.title = 'Опубликовано за последние 7 дней'; badge.hidden = !isNew(value);
    meta.append(text, badge); return meta;
  }
  window.TonkoPublication = Object.freeze({timestamp, compareNewest, isNew, create, refresh});
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => refresh(), {once:true});
  else refresh();
  setInterval(() => { if (!document.hidden) refresh(); }, 60000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  addEventListener('pageshow', () => refresh());
})();
