/* One on-demand player; all catalogue entries and external links also work without JS. */
(() => {
  'use strict';
  const library = document.getElementById('video-library');
  if (!library) return;
  const videos = window.TONKO_VIDEOS || [];
  if (!videos.length) return;
  const $ = id => document.getElementById(id);
  const key = 'tonko-video-shelf-v1';
  const ids = new Set(videos.map(v => v.id));
  const languages = { ru: 'На русском', en: 'На английском', none: 'Без речи' };
  const buttons = [...document.querySelectorAll('[data-video-topic]')];
  const cards = [...document.querySelectorAll('[data-video-card]')];
  const readSaved = () => {
    try {
      const raw = JSON.parse(localStorage.getItem(key) || '[]');
      return new Set(Array.isArray(raw) ? raw.filter(id => ids.has(id)) : []);
    } catch { return new Set(); }
  };
  const normal = text => text.toLocaleLowerCase('ru').replaceAll('ё', 'е');
  let saved = readSaved();
  let topic = 'all', savedOnly = false, current = videos[0], shown = [...videos];
  let playing = false;
  const params = new URLSearchParams(location.search);
  if (buttons.some(b => b.dataset.videoTopic === params.get('topic'))) topic = params.get('topic');
  savedOnly = params.get('saved') === '1';
  $('video-search').value = params.get('q') || '';
  if (languages[params.get('language')]) $('video-language').value = params.get('language');
  current = videos.find(v => v.id === params.get('video')) || current;

  function updateURL() {
    const url = new URL(location.href);
    const values = { topic: topic === 'all' ? '' : topic, saved: savedOnly ? '1' : '', q: $('video-search').value.trim(), language: $('video-language').value === 'all' ? '' : $('video-language').value };
    for (const [name, value] of Object.entries(values)) value ? url.searchParams.set(name, value) : url.searchParams.delete(name);
    history.replaceState(null, '', url);
  }

  function filter(update = true) {
    const query = normal($('video-search').value.trim());
    const language = $('video-language').value;
    shown = videos.filter(v => (topic === 'all' || v.topics.includes(topic)) &&
      (!savedOnly || saved.has(v.id)) && (language === 'all' || v.language === language) &&
      normal([v.title, v.originalTitle, v.description, v.author].join(' ')).includes(query));
    const visible = new Set(shown.map(v => v.id));
    for (const card of cards) card.hidden = !visible.has(card.dataset.videoCard);
    for (const button of buttons) button.setAttribute('aria-pressed', String(button.dataset.videoTopic === topic));
    $('video-saved').setAttribute('aria-pressed', String(savedOnly));
    $('video-saved-count').textContent = saved.size;
    $('video-count').textContent = `Показано ${shown.length} из ${videos.length} видео${savedOnly ? ' · Смотреть позже' : ''}`;
    $('video-empty').hidden = shown.length !== 0;
    $('video-empty-text').textContent = savedOnly && saved.size === 0 ? 'Нажмите «Смотреть позже» у интересного ролика. Он появится в вашей подборке.' : 'Попробуйте другую тему, язык или сократите запрос.';
    $('video-next').disabled = shown.length === 0 || (shown.length === 1 && shown[0].id === current.id);
    for (const button of document.querySelectorAll('[data-video-save]')) {
      const active = saved.has(button.dataset.videoSave);
      const video = videos.find(v => v.id === button.dataset.videoSave);
      button.setAttribute('aria-pressed', String(active));
      button.textContent = active ? 'Сохранено ✓' : 'Смотреть позже';
      button.setAttribute('aria-label', `${active ? 'Убрать из подборки' : 'Смотреть позже'}: ${video.title}`);
    }
    if (update) updateURL();
  }

  function poster() {
    const screen = $('video-screen');
    screen.replaceChildren(); // Removing the iframe stops audio, playback and its network session.
    playing = false;
    const image = document.createElement('img');
    image.src = current.thumbnail; image.alt = current.originalTitle;
    image.width = 480; image.height = 360;
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'video-start'; button.dataset.videoPlay = current.id;
    button.innerHTML = '<span aria-hidden="true">▶</span><span>Смотреть</span>';
    button.setAttribute('aria-label', `Смотреть: ${current.title}`);
    screen.append(image, button);
    $('video-stop').hidden = true;
  }

  function selectVideo(video, play = false, scroll = false) {
    current = video;
    $('video-current-title').textContent = video.title;
    $('video-current-description').textContent = video.description;
    $('video-current-kind').textContent = `${video.kind} · ${languages[video.language]}`;
    $('video-current-author').textContent = video.author + ' ↗';
    $('video-current-author').href = video.authorUrl;
    $('video-original').href = video.url;
    $('video-share-link').hidden = true;
    $('video-status').textContent = '';
    poster();
    if (play) {
      const frame = document.createElement('iframe');
      const embed = new URL(`https://www.youtube-nocookie.com/embed/${video.id}`);
      embed.searchParams.set('autoplay', '1');
      embed.searchParams.set('playsinline', '1');
      embed.searchParams.set('rel', '0');
      embed.searchParams.set('origin', location.origin);
      frame.src = embed.href;
      frame.title = `${video.originalTitle} · ${video.author}`;
      frame.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
      frame.allowFullscreen = true;
      frame.referrerPolicy = 'strict-origin-when-cross-origin';
      $('video-screen').replaceChildren(frame);
      $('video-stop').hidden = false;
      playing = true;
      const url = new URL(location.href); url.searchParams.set('video', video.id);
      history.replaceState(null, '', url);
    }
    $('video-next').disabled = shown.length === 0 || (shown.length === 1 && shown[0].id === current.id);
    if (scroll) {
      $('video-player').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' });
      $('video-player').focus({ preventScroll: true });
    }
  }

  document.addEventListener('click', event => {
    const play = event.target.closest('[data-video-play]');
    if (play) {
      const video = videos.find(v => v.id === play.dataset.videoPlay);
      if (video) selectVideo(video, true, !play.closest('#video-screen'));
    }
    const save = event.target.closest('[data-video-save]');
    if (save) {
      const id = save.dataset.videoSave;
      if (!ids.has(id)) return;
      const next = new Set(saved);
      next.has(id) ? next.delete(id) : next.add(id);
      try {
        localStorage.setItem(key, JSON.stringify([...next]));
        saved = next;
        $('video-save-status').textContent = saved.has(id) ? 'Видео сохранено в этом браузере.' : 'Видео удалено из вашей подборки.';
        filter();
        // Do not leave focus inside a card just hidden by the saved filter.
        if (savedOnly && !saved.has(id)) $('video-saved').focus();
      } catch {
        $('video-save-status').textContent = 'Браузер не разрешил сохранение. Вы можете скопировать ссылку на видео.';
      }
    }
  });
  for (const button of buttons) button.addEventListener('click', () => { topic = button.dataset.videoTopic; filter(); });
  $('video-saved').addEventListener('click', () => { savedOnly = !savedOnly; filter(); });
  $('video-search').addEventListener('input', () => filter());
  $('video-language').addEventListener('change', () => filter());
  $('video-reset').addEventListener('click', () => {
    topic = 'all'; savedOnly = false; $('video-search').value = ''; $('video-language').value = 'all'; filter(); $('video-search').focus();
  });
  $('video-stop').addEventListener('click', () => { poster(); $('video-screen').querySelector('button').focus(); });
  $('video-next').addEventListener('click', () => {
    if (!shown.length) return;
    const index = shown.findIndex(v => v.id === current.id);
    selectVideo(shown[(index + 1) % shown.length], true);
  });
  $('video-copy').addEventListener('click', async () => {
    const url = new URL('videos.html', location.href); url.searchParams.set('video', current.id);
    try {
      await navigator.clipboard.writeText(url.href);
      $('video-status').textContent = 'Ссылка скопирована.';
    } catch {
      const input = $('video-share-link'); input.value = url.href; input.hidden = false; input.focus(); input.select();
      $('video-status').textContent = 'Скопируйте выделенную ссылку.';
    }
  });
  addEventListener('storage', event => { if (event.key === key || event.key === null) { saved = readSaved(); filter(false); } });
  addEventListener('pagehide', () => { if (playing) poster(); });
  for (const element of document.querySelectorAll('.video-tools, .video-player-actions, [data-video-play], [data-video-save]')) element.hidden = false;
  selectVideo(current);
  filter(false);
})();
