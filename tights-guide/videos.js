/* One on-demand player; all catalogue entries and external links also work without JS. */
(() => {
  'use strict';
  const library = document.getElementById('video-library');
  if (!library) return;
  const videos = window.TONKO_VIDEOS || [];
  if (!videos.length) return;
  const $ = id => document.getElementById(id);
  const key = 'tonko-video-shelf-v1';
  const memory=window.TonkoVideoMemory;
  let progressTimer=0;
  // A play click is the complete setup. Platform help appears only on failure.
  const youtubeHelp=document.createElement('p');
  youtubeHelp.id='video-youtube-help';youtubeHelp.className='video-error-help';youtubeHelp.hidden=true;
  youtubeHelp.textContent='Если YouTube показывает проверку «не бот» или требует вход, это ограничение самого сервиса. ТОНКО не может снять его. Можно выбрать ролик Vimeo или видео с сайта бренда.';
  $('video-playback-status').after(youtubeHelp);
  const ids = new Set(videos.map(v => v.id));
  const languages = { ru: 'На русском', en: 'На английском', none: 'Без речи', original: 'Язык оригинала' };
  const provider = video => ['vimeo','native'].includes(video.provider) ? video.provider : 'youtube';
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
  let playing = false, player = null, playerSession = 0, playerTimer = 0, apiPromise = null;
  let vimeoPromise = null;
  const params = new URLSearchParams(location.search);
  if (buttons.some(b => b.dataset.videoTopic === params.get('topic'))) topic = params.get('topic');
  savedOnly = params.get('saved') === '1';
  $('video-search').value = params.get('q') || '';
  if (languages[params.get('language')]) $('video-language').value = params.get('language');
  if (['youtube', 'vimeo','native'].includes(params.get('provider'))) $('video-provider').value = params.get('provider');
  current = videos.find(v => v.id === params.get('video')) || current;

  function updateURL() {
    const url = new URL(location.href);
    const values = { topic: topic === 'all' ? '' : topic, saved: savedOnly ? '1' : '', q: $('video-search').value.trim(), language: $('video-language').value === 'all' ? '' : $('video-language').value };
    values.provider = $('video-provider').value === 'all' ? '' : $('video-provider').value;
    for (const [name, value] of Object.entries(values)) value ? url.searchParams.set(name, value) : url.searchParams.delete(name);
    history.replaceState(null, '', url);
  }

  function filter(update = true) {
    const query = normal($('video-search').value.trim());
    const language = $('video-language').value;
    shown = videos.filter(v => (topic === 'all' || v.topics.includes(topic)) &&
      (!savedOnly || saved.has(v.id)) && (language === 'all' || v.language === language) &&
      ($('video-provider').value === 'all' || provider(v) === $('video-provider').value) &&
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

  function playbackStatus(message = '', retry = false, alternative = false) {
    $('video-playback-status').textContent = message;
    $('video-playback-status').hidden = !message;
    $('video-retry').hidden = !retry;
    $('video-alternative').hidden = !alternative || provider(current) === 'native';
    $('video-alternative').textContent = videos.some(v=>provider(v)==='native') ? 'Видео с сайта бренда' : 'Другие видео';
    youtubeHelp.hidden = !alternative || provider(current) !== 'youtube';
  }

  function loadVimeoAPI() {
    if (window.Vimeo?.Player) return Promise.resolve(window.Vimeo);
    if (vimeoPromise) return vimeoPromise;
    vimeoPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      const fail = () => { clearTimeout(timer); script.remove(); reject(new Error('Vimeo API unavailable')); };
      const timer = setTimeout(fail, 18000);
      script.src = 'https://player.vimeo.com/api/player.js'; script.async = true;
      script.onload = () => { clearTimeout(timer); window.Vimeo?.Player ? resolve(window.Vimeo) : fail(); };
      script.onerror = fail; document.head.append(script);
    }).catch(error => { vimeoPromise = null; throw error; });
    return vimeoPromise;
  }

  function playNative(video,session){
    const media=document.createElement('video');
    media.controls=true;media.playsInline=true;media.preload='metadata';media.poster=video.thumbnail;
    media.setAttribute('aria-label',video.title);media.src=video.streamUrl;
    const active=()=>playing&&session===playerSession;
    player={destroy(){media.pause();media.removeAttribute('src');media.load();}};
    const status=(text='',retry=false)=>{if(active()){$('video-screen').setAttribute('aria-busy','false');playbackStatus(text,retry);}};
    media.addEventListener('loadedmetadata',()=>{if(active()){const resume=memory.get(video.id);if(resume>0&&resume<media.duration)media.currentTime=resume;}});
    media.addEventListener('timeupdate',()=>{if(active())memory.save(video.id,media.currentTime,media.duration);});
    media.addEventListener('playing',()=>status());
    media.addEventListener('ended',()=>{if(active()){memory.save(video.id,0,media.duration);status('Видео закончилось. Можно выбрать следующее из подборки.');}});
    media.addEventListener('error',()=>status('Не удалось загрузить видео с сервера бренда. Повторите запуск или выберите другой ролик.',true));
    $('video-screen').replaceChildren(media);
    media.play().catch(()=>status('Нажмите ▶ внутри плеера, чтобы начать просмотр.'));
  }

  function observeVimeo(frame, session) {
    const active = () => playing && session === playerSession;
    const status = (text = '', retry = false) => {
      if (!active()) return;
      clearTimeout(playerTimer); $('video-screen').setAttribute('aria-busy', 'false');
      playbackStatus(text, retry, retry);
    };
    playerTimer = setTimeout(() => status('Плеер загружается дольше обычного. Можно подождать или повторить запуск.', true), 25000);
    loadVimeoAPI().then(Vimeo => {
      if (!active()) return;
      const instance = new Vimeo.Player(frame); player = instance;
      const videoId=current.id;
      instance.on('timeupdate',data=>{if(active())memory.save(videoId,data.seconds,data.duration);});
      instance.on('play', () => status());
      instance.on('ended', () => {if(!active())return;memory.save(videoId,0,current.duration);status('Видео закончилось. Можно выбрать следующее из подборки.');});
      instance.on('error', () => status('Vimeo не смог запустить видео. Проверьте сообщение в плеере или повторите запуск.', true));
      return instance.ready().then(async () => {
        if (!active()) return;
        const resume=memory.get(videoId);if(resume>0)await instance.setCurrentTime(resume).catch(()=>{});
        if (!active()) return;
        return instance.play().catch(() => status('Нажмите ▶ внутри плеера, чтобы начать просмотр.'));
      });
    }).catch(() => status('Используйте кнопки внутри плеера Vimeo. Если он не загрузился, повторите запуск.', true));
  }

  // Load the official API only after a play click. The iframe also works if the API fails.
  function loadPlayerAPI() {
    if (window.YT?.Player) return Promise.resolve(window.YT);
    if (apiPromise) return apiPromise;
    apiPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      const previous = window.onYouTubeIframeAPIReady;
      const ready = () => { cleanup(); resolve(window.YT); if (typeof previous === 'function') previous(); };
      const cleanup = () => {
        clearTimeout(timer);
        script.onerror = null;
        if (window.onYouTubeIframeAPIReady === ready) window.onYouTubeIframeAPIReady = previous;
      };
      const fail = () => { cleanup(); script.remove(); reject(new Error('YouTube API unavailable')); };
      const timer = setTimeout(fail, 15000);
      window.onYouTubeIframeAPIReady = ready;
      script.src = 'https://www.youtube.com/iframe_api';
      script.async = true;
      script.referrerPolicy = 'strict-origin-when-cross-origin';
      script.onerror = fail;
      document.head.append(script);
    }).catch(error => { apiPromise = null; throw error; });
    return apiPromise;
  }

  function observePlayer(frame, session) {
    const active = () => playing && session === playerSession;
    let hasProblem = false;
    playerTimer = setTimeout(() => {
      if (!active()) return;
      $('video-screen').setAttribute('aria-busy', 'false');
      playbackStatus('Плеер долго загружается. Если видео не появилось, повторите запуск или выберите другое.', true, true);
    }, 18000);
    loadPlayerAPI().then(YT => {
      if (!active()) return;
      player = new YT.Player(frame, { events: {
        onReady(event) {
          if (!active()) return;
          clearTimeout(playerTimer);
          const videoId=current.id;
          const resume=memory.get(videoId);if(resume>0)event.target.seekTo(resume,true);
          progressTimer=setInterval(()=>{if(active()){try{memory.save(videoId,event.target.getCurrentTime(),event.target.getDuration());}catch{}}},2000);
          $('video-screen').setAttribute('aria-busy', 'false');
          if (!hasProblem) playbackStatus();
        },
        onStateChange(event) {
          if (!active()) return;
          if ([0, 1, 2, 5].includes(event.data)) {
            clearTimeout(playerTimer);
            $('video-screen').setAttribute('aria-busy', 'false');
          }
          if ([0, 1, 2].includes(event.data) && (!hasProblem || event.data === 1)) {
            hasProblem = false;
            playbackStatus(event.data === 0 ? 'Видео закончилось. Можно выбрать следующее из подборки.' : '');
          }
        },
        onAutoplayBlocked() {
          if (!active()) return;
          clearTimeout(playerTimer);
          hasProblem = true;
          $('video-screen').setAttribute('aria-busy', 'false');
          playbackStatus('Браузер ждёт нажатия: нажмите ▶ внутри плеера, чтобы смотреть здесь.');
        },
        onError(event) {
          if (!active()) return;
          clearTimeout(playerTimer);
          hasProblem = true;
          $('video-screen').setAttribute('aria-busy', 'false');
          const errors = {
            2: 'Не удалось открыть этот ролик. Выберите другое видео из подборки.',
            5: 'Браузер не смог воспроизвести видео. Попробуйте повторить запуск.',
            100: 'Ролик удалён или стал закрытым. Выберите другое видео из подборки.',
            101: 'YouTube не разрешил запуск видео. Причина указана внутри плеера. Можно повторить запуск или выбрать другое видео.',
            150: 'YouTube не разрешил запуск видео. Причина указана внутри плеера. Можно повторить запуск или выбрать другое видео.',
            153: 'YouTube не смог подтвердить адрес этой страницы. Попробуйте обновить её или выберите другое видео.'
          };
          playbackStatus(errors[event.data] || 'Не удалось запустить видео. Посмотрите сообщение YouTube в плеере или повторите запуск.', ![2, 100].includes(event.data), true);
        }
      } });
    }).catch(() => {
      if (!active()) return;
      clearTimeout(playerTimer);
      $('video-screen').setAttribute('aria-busy', 'false');
      playbackStatus('Используйте кнопки внутри плеера. Если он не загрузился, повторите запуск.', true, true);
    });
  }

  function poster() {
    clearInterval(progressTimer);
    ++playerSession; // Ignore late API callbacks after another selection or closing.
    clearTimeout(playerTimer);
    if (player) { try { Promise.resolve(player.destroy()).catch(() => {}); } catch { /* The iframe may already be detached. */ } }
    player = null;
    const screen = $('video-screen');
    screen.replaceChildren(); // Removing the iframe stops audio, playback and its network session.
    screen.setAttribute('aria-busy', 'false');
    playing = false;
    playbackStatus();
    const image = document.createElement('img');
    image.src = current.thumbnail; image.alt = current.originalTitle;
    image.width = current.thumbnailWidth || 480; image.height = current.thumbnailHeight || 360;
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'video-start'; button.dataset.videoPlay = current.id;
    button.innerHTML = '<span aria-hidden="true">▶</span><span>Смотреть на сайте</span>';
    const resume=memory.get(current.id);
    if(resume>0)button.lastElementChild.textContent=`Продолжить с ${Math.floor(resume/60)}:${String(resume%60).padStart(2,'0')}`;
    button.setAttribute('aria-label', `Смотреть на сайте: ${current.title}`);
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
    const isVimeo = provider(video) === 'vimeo',isNative=provider(video)==='native';
    const name = isNative ? 'Snag · HTML5' : isVimeo ? 'Vimeo' : 'YouTube';
    $('video-original').textContent = isNative?'Источник: официальный сайт Snag ↗':`Оригинал на ${name} ↗`;
    $('video-viewing-note').textContent = isNative?'Плеер ТОНКО · Без аккаунта':isVimeo ? 'Vimeo · Просмотр на ТОНКО' : 'YouTube · Просмотр на ТОНКО';
    $('video-connection-note').textContent = isNative?'Видео поступает с официального CDN Snag после нажатия. Просмотр, звук, скорость и полный экран управляются здесь.':`После нажатия загружается плеер ${name}. Звук, субтитры и полный экран управляются внутри него.`;
    $('video-screen').classList.toggle('is-portrait', (video.thumbnailHeight||360)>(video.thumbnailWidth||480));
    $('video-share-link').hidden = true;
    $('video-status').textContent = '';
    poster();
    if (play) {
      if(isNative){
        playing=true;$('video-stop').hidden=false;$('video-screen').setAttribute('aria-busy','true');playbackStatus('Загружаем видео…');
        playNative(video,playerSession);
      }else{
      const frame = document.createElement('iframe');
      const embed = new URL(isVimeo ? `https://player.vimeo.com/video/${video.providerId}` : `https://www.youtube.com/embed/${video.id}`);
      embed.searchParams.set('autoplay', '1');
      embed.searchParams.set('playsinline', '1');
      if (isVimeo) embed.searchParams.set('dnt', '1');
      else {
        embed.searchParams.set('rel', '0');
        embed.searchParams.set('enablejsapi', '1');
        embed.searchParams.set('origin', location.origin);
      }
      frame.id = 'tonko-video-player';
      frame.src = embed.href;
      frame.title = `${video.originalTitle} · ${video.author}`;
      frame.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
      frame.allowFullscreen = true;
      frame.referrerPolicy = 'strict-origin-when-cross-origin';
      $('video-screen').replaceChildren(frame);
      $('video-stop').hidden = false;
      playing = true;
      $('video-screen').setAttribute('aria-busy', 'true');
      playbackStatus('Загружаем плеер…');
      isVimeo ? observeVimeo(frame, playerSession) : observePlayer(frame, playerSession);
      if (!scroll) frame.focus({ preventScroll: true });
      }
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
  $('video-provider').addEventListener('change', () => filter());
  $('video-reset').addEventListener('click', () => {
    topic = 'all'; savedOnly = false; $('video-search').value = ''; $('video-language').value = 'all'; $('video-provider').value = 'all'; filter(); $('video-search').focus();
  });
  $('video-stop').addEventListener('click', () => { poster(); $('video-screen').querySelector('button').focus(); });
  $('video-retry').addEventListener('click', () => selectVideo(current, true));
  $('video-alternative').addEventListener('click', () => {
    topic = 'all'; savedOnly = false; $('video-search').value = ''; $('video-language').value = 'all'; $('video-provider').value = videos.some(v=>provider(v)==='native')?'native':'vimeo';
    filter(); if (shown.length) selectVideo(shown[0], true);
  });
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
