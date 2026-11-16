(() => {
  'use strict';
  if (document.getElementById('tonko-assistant')) return;
  const script = document.currentScript;
  const base = new URL('.', script?.src || location.href);
  const STORAGE_KEY = 'tonko.assistant.v1';
  const MAX_MESSAGE = 1600;
  const el = (tag, className, text) => {
    const node = document.createElement(tag); if (className) node.className = className;
    if (text !== undefined) node.textContent = text; return node;
  };
  const icon = (name) => {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('fill', 'none'); svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '1.5'); svg.setAttribute('stroke-linecap', 'round'); svg.setAttribute('stroke-linejoin', 'round');
    const path = document.createElementNS(svg.namespaceURI, 'path');
    path.setAttribute('d', name === 'close' ? 'm6 6 12 12M6 18 18 6' : name === 'send' ? 'M12 19V5m-6 6 6-6 6 6' : 'M20 11.5a8 8 0 0 1-8 8H5l-3 2v-10a9 9 0 1 1 18 0ZM7 10h8M7 14h5');
    svg.append(path); return svg;
  };
  const safeLink = href => {
    if (typeof href !== 'string' || !/^[a-z0-9-]+\.html(?:[?#].*)?$/.test(href)) return null;
    const url = new URL(href, base);
    return url.origin === base.origin && url.pathname.startsWith(base.pathname) ? url.href : null;
  };
  const cleanMessage = item => {
    if (!item || !['user', 'assistant'].includes(item.role) || typeof item.content !== 'string' || !item.content.trim() || item.content.length > 5300) return null;
    return { role: item.role, content: item.content, sources: (Array.isArray(item.sources) ? item.sources : []).slice(0, 3).filter(s => s && typeof s.title === 'string' && s.title.length <= 160 && safeLink(s.href)).map(s => ({ title: s.title, href: s.href })) };
  };
  let messages = [];
  try { const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '[]'); if (Array.isArray(saved)) messages = saved.slice(-24).map(cleanMessage).filter(Boolean); } catch { /* private mode / corrupt old storage */ }
  let config = null, pending = null, opener = null, sequence = 0;

  const launcher = el('button', 'tonko-assistant-launcher');
  launcher.type = 'button'; launcher.setAttribute('aria-controls', 'tonko-assistant');
  launcher.setAttribute('aria-haspopup', 'dialog'); launcher.setAttribute('aria-expanded', 'false');
  launcher.append(icon('chat'), el('span', '', 'Спросить ТОНКО'));
  const dialog = el('dialog', 'tonko-assistant'); dialog.id = 'tonko-assistant';
  dialog.setAttribute('aria-labelledby', 'tonko-assistant-title');
  const header = el('header', 'tonko-assistant-header');
  const heading = el('div'); heading.append(el('p', 'tonko-assistant-eyebrow', 'ТОНКО / ИИ-помощник'));
  const title = el('h2', '', 'Помочь с выбором?'); title.id = 'tonko-assistant-title'; heading.append(title);
  const close = el('button', 'tonko-assistant-icon'); close.type = 'button'; close.setAttribute('aria-label', 'Закрыть помощника'); close.append(icon('close'));
  header.append(heading, close);
  const toolbar = el('div', 'tonko-assistant-toolbar');
  toolbar.append(el('span', '', 'DEN · посадка · уход · образы'));
  const clear = el('button', 'tonko-assistant-clear', 'Очистить'); clear.type = 'button'; clear.setAttribute('aria-label', 'Очистить переписку в этой вкладке'); toolbar.append(clear);
  const conversation = el('div', 'tonko-assistant-conversation');
  conversation.setAttribute('role', 'log'); conversation.setAttribute('aria-label', 'Переписка с помощником'); conversation.setAttribute('aria-live', 'polite'); conversation.setAttribute('aria-relevant', 'additions'); conversation.tabIndex = 0;
  const welcome = el('section', 'tonko-assistant-welcome');
  welcome.append(el('span', 'tonko-assistant-monogram', 'Т'), el('h3', '', 'У каждой пары — свои детали.'), el('p', '', 'Разберёмся в плотности, размере и составе. Найдём упаковку или материал для вашего вопроса.'));
  const suggestions = el('div', 'tonko-assistant-suggestions'); suggestions.setAttribute('aria-label', 'Примеры вопросов');
  [ ['20 или 40 DEN?', 'Чем отличаются 20 и 40 DEN и как выбрать?'], ['Как узнать размер?', 'Как узнать свой размер колготок?'], ['Мужской образ', 'Помоги составить мужской образ с колготками.'], ['Бережный уход', 'Как ухаживать за тонкими колготками?'] ].forEach(([label, question]) => {
    const button = el('button', '', label); button.type = 'button';
    button.addEventListener('click', () => { input.value = question; updateInput(); input.focus(); if (isReady()) form.requestSubmit(); });
    suggestions.append(button);
  });
  welcome.append(suggestions);
  const notice = el('div', 'tonko-assistant-notice', 'Проверяем доступность помощника…');
  notice.setAttribute('role', 'status');
  const busy = el('div', 'tonko-assistant-busy', 'Подбираю ответ по материалам ТОНКО…'); busy.setAttribute('role', 'status'); busy.hidden = true;
  const form = el('form', 'tonko-assistant-form');
  const label = el('label', 'tonko-assistant-sr-only', 'Ваш вопрос о колготках'); label.htmlFor = 'tonko-assistant-input';
  const input = el('textarea'); input.id = 'tonko-assistant-input'; input.name = 'message'; input.rows = 2; input.maxLength = MAX_MESSAGE;
  input.placeholder = 'Например: какие колготки выбрать под шорты?'; input.autocomplete = 'off';
  input.setAttribute('aria-describedby', 'tonko-assistant-hint');
  const compose = el('div', 'tonko-assistant-compose');
  const send = el('button', 'tonko-assistant-send'); send.type = 'submit'; send.setAttribute('aria-label', 'Отправить вопрос'); send.append(icon('send')); send.disabled = true;
  compose.append(input, send);
  const actions = el('div', 'tonko-assistant-form-bottom');
  const hint = el('span', '', 'Enter — отправить · Shift+Enter — новая строка'); hint.id = 'tonko-assistant-hint';
  const stop = el('button', 'tonko-assistant-stop', 'Остановить'); stop.type = 'button'; stop.hidden = true;
  actions.append(hint, stop);
  const privacy = el('p', 'tonko-assistant-privacy', 'Вопрос и часть переписки отправляются OpenAI. История хранится в этой вкладке. Не указывайте личные данные. ');
  const privacyLink = el('a', '', 'Подробнее'); privacyLink.href = new URL('privacy.html', base).href; privacy.append(privacyLink);
  form.append(label, compose, actions, privacy);
  dialog.append(header, toolbar, conversation, notice, busy, form);
  document.body.append(launcher, dialog);

  function persist() {
    try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-24))); }
    catch { privacy.firstChild.textContent = 'Вопрос и часть переписки отправляются OpenAI. Браузер не разрешил сохранить историю — она исчезнет при обновлении страницы. Не указывайте личные данные. '; }
  }
  function appendMessage(item) {
    const article = el('article', `tonko-assistant-message is-${item.role}`);
    article.append(el('p', 'tonko-assistant-speaker', item.role === 'user' ? 'Вы' : 'ТОНКО · ИИ'));
    article.append(el('p', 'tonko-assistant-text', item.content));
    if (item.role === 'assistant' && item.sources?.length) {
      const sources = el('ul', 'tonko-assistant-sources'); sources.setAttribute('aria-label', 'Материалы к ответу');
      for (const source of item.sources) {
        const href = safeLink(source.href); if (!href) continue;
        const li = el('li'); const a = el('a', '', source.title + ' →'); a.href = href; li.append(a); sources.append(li);
      }
      article.append(sources);
    }
    conversation.append(article);
  }
  function render() {
    conversation.replaceChildren();
    if (!messages.length) conversation.append(welcome); else messages.forEach(appendMessage);
    clear.disabled = !messages.length && !pending;
    scrollEnd();
  }
  function scrollEnd() { requestAnimationFrame(() => { conversation.scrollTop = conversation.scrollHeight; }); }
  function isReady() { return Boolean(config?.enabled && config.endpoint && config.publishableKey); }
  function updateInput() {
    send.disabled = Boolean(pending) || !isReady() || !input.value.trim();
    input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 108) + 'px';
    hint.textContent = input.value.length > MAX_MESSAGE - 200 ? `${input.value.length} / ${MAX_MESSAGE} знаков` : matchMedia('(pointer: coarse)').matches ? 'Нажмите ↑, чтобы отправить вопрос' : 'Enter — отправить · Shift+Enter — новая строка';
  }
  function setNotice(text, error = false) {
    notice.textContent = text; notice.hidden = !text; notice.classList.toggle('is-error', error);
    notice.setAttribute('role', error ? 'alert' : 'status');
  }
  function setPending(controller) {
    pending = controller; busy.hidden = !pending; stop.hidden = !pending;
    input.readOnly = Boolean(pending); conversation.setAttribute('aria-busy', String(Boolean(pending)));
    updateInput(); clear.disabled = !messages.length && !pending;
  }
  function cancel(message = 'Ответ остановлен. Можно задать следующий вопрос.') {
    if (!pending) return;
    sequence++; pending.abort(); setPending(null); setNotice(message); input.focus();
  }
  function historyForRequest() {
    const history = messages.slice(0, -1).slice(-8).map(m => ({ role: m.role, content: m.content.slice(0, 3000) }));
    while (history.reduce((n, m) => n + m.content.length, 0) > 6000) history.shift();
    return history;
  }
  async function submit(event) {
    event.preventDefault();
    if (pending || !isReady() || !input.value.trim()) return;
    const question = input.value.trim().slice(0, MAX_MESSAGE);
    messages.push({ role: 'user', content: question, sources: [] }); messages = messages.slice(-24);
    input.value = ''; persist(); render(); setNotice('');
    const controller = new AbortController(); const requestId = ++sequence; setPending(controller);
    let timedOut = false;
    const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, 35000);
    try {
      const r = await fetch(config.endpoint, { method: 'POST', credentials: 'omit', cache: 'no-store', headers: { 'Content-Type': 'application/json', apikey: config.publishableKey }, signal: controller.signal,
        body: JSON.stringify({ message: question, history: historyForRequest() }) });
      const data = await r.json();
      if (requestId !== sequence) return;
      if (!r.ok) {
        if (r.status === 429) {
          const seconds = Number(data.retryAfter || r.headers.get('retry-after'));
          throw new Error(seconds > 3600 ? 'На сегодня лимит ответов исчерпан. Вернитесь завтра; материалы сайта доступны сейчас.' : 'Сейчас слишком много вопросов. Попробуйте через несколько минут.');
        }
        if (data.error === 'not_configured') throw new Error('Помощник ещё подключается. Пока можно открыть мастерскую выбора или архив упаковок.');
        if (data.error === 'timeout') throw new Error('Ответ занял больше времени, чем ожидалось. Попробуйте задать вопрос ещё раз.');
        if (r.status === 400 || r.status === 413) throw new Error('Сократите вопрос или очистите длинную переписку и попробуйте снова.');
        throw new Error('Помощник временно недоступен. Попробуйте немного позже.');
      }
      if (typeof data.answer !== 'string' || !data.answer.trim() || data.answer.length > 5000 || !Array.isArray(data.sources)) throw new Error('Не удалось прочитать ответ. Попробуйте ещё раз.');
      const content = data.answer.trim() + (typeof data.nextQuestion === 'string' && data.nextQuestion.trim() ? '\n\n' + data.nextQuestion.trim().slice(0, 240) : '');
      const item = cleanMessage({ role: 'assistant', content, sources: data.sources });
      if (!item) throw new Error('Не удалось прочитать ответ. Попробуйте ещё раз.');
      messages.push(item); persist(); appendMessage(item); scrollEnd();
    } catch (error) {
      if (requestId !== sequence) return;
      if (timedOut) setNotice('Ответ занял слишком много времени. Попробуйте ещё раз.', true);
      else if (error.name !== 'AbortError') setNotice(error instanceof TypeError || error instanceof SyntaxError ? 'Не удалось связаться с помощником. Проверьте соединение и попробуйте позже.' : error.message, true);
      input.value = question;
    } finally {
      clearTimeout(timeout);
      if (requestId === sequence) { setPending(null); if (dialog.open) input.focus({ preventScroll: true }); }
    }
  }
  function openPanel() {
    if (dialog.open) return;
    opener = document.activeElement; dialog.showModal(); launcher.setAttribute('aria-expanded', 'true');
    input.focus({ preventScroll: true }); scrollEnd();
  }
  launcher.addEventListener('click', openPanel);
  document.addEventListener('click', event => {
    const target = event.target.closest('[data-assistant-open]');
    if (target) { event.preventDefault(); openPanel(); }
  });
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => { cancel(); launcher.setAttribute('aria-expanded', 'false'); opener?.focus({ preventScroll: true }); });
  dialog.addEventListener('keydown', event => {
    if (event.key !== 'Tab') return;
    const focusable = [...dialog.querySelectorAll('button:not([disabled]),a[href],textarea:not([disabled]),[tabindex]:not([tabindex="-1"])')].filter(node => node.getClientRects().length);
    const first = focusable[0], last = focusable.at(-1);
    if (event.shiftKey && (document.activeElement === first || !focusable.includes(document.activeElement))) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  });
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const r = dialog.getBoundingClientRect();
    if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close();
  });
  clear.addEventListener('click', () => {
    cancel(''); messages = []; try { sessionStorage.removeItem(STORAGE_KEY); } catch { /* unavailable */ }
    input.value = ''; render(); updateInput(); setNotice(isReady() ? 'Переписка очищена.' : 'Помощник ещё подключается. Материалы сайта доступны ниже.'); input.focus();
  });
  stop.addEventListener('click', () => cancel());
  form.addEventListener('submit', submit);
  input.addEventListener('input', updateInput);
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && !matchMedia('(pointer: coarse)').matches) {
      event.preventDefault(); if (!send.disabled) form.requestSubmit();
    }
  });
  render();
  fetch(new URL('data/assistant-config.json', base), { cache: 'no-store', credentials: 'same-origin' })
    .then(r => { if (!r.ok) throw new Error(); return r.json(); })
    .then(value => {
      let endpoint = '';
      try {
        const url = new URL(value.endpoint);
        const localPage = ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname);
        const production = url.protocol === 'https:' && /^[a-z0-9]+\.supabase\.co$/.test(url.hostname) && url.pathname === '/functions/v1/tonko-assistant';
        const localEndpoint = localPage && url.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
        if ((production || localEndpoint) && !url.username && !url.password && !url.search && !url.hash) endpoint = url.href;
      } catch { /* disabled until a valid server endpoint is configured */ }
      const publishableKey = typeof value.publishableKey === 'string' && /^sb_publishable_[A-Za-z0-9_-]+$/.test(value.publishableKey) ? value.publishableKey : '';
      config = { enabled: value.enabled === true && Boolean(endpoint && publishableKey), endpoint, publishableKey };
      setNotice(isReady() ? '' : 'Помощник ещё подключается. Пока загляните в мастерскую выбора или архив упаковок.');
      if (!isReady()) {
        const links = el('span', 'tonko-assistant-offline-links');
        for (const [title, href] of [['Как выбрать →', 'guide.html'], ['Упаковки →', 'packaging.html']]) {
          const a = el('a', '', title); a.href = new URL(href, base).href; links.append(a);
        }
        notice.append(links);
      }
      updateInput();
    }).catch(() => { setNotice('Не удалось подключить помощника. Обновите страницу или откройте раздел «Как выбрать».', true); updateInput(); });
})();
