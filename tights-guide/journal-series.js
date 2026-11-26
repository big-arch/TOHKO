(() => {
  'use strict';

  function initArchive() {
    const frame = document.querySelector('.archive-frame');
    if (!frame) return;
    const choices = document.querySelector('.archive-choices');
    const caption = document.getElementById('archive-caption');
    const image = frame.querySelector('img');
    const fullFrameSize = image.sizes;
    const buttons = choices.querySelectorAll('button');
    choices.hidden = false;
    buttons.forEach(button => button.addEventListener('click', () => {
      const view = button.dataset.archiveView;
      frame.dataset.view = view;
      image.sizes = view === 'whole' ? fullFrameSize : Math.ceil(frame.clientWidth * 2.8) + 'px';
      caption.textContent = button.dataset.caption;
      buttons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    }));
  }

  function initBatch() {
    const form = document.getElementById('batch-form');
    if (!form) return;
    const result = document.getElementById('batch-result');
    const numbers = new Intl.NumberFormat('ru-RU');
    const plurals = new Intl.PluralRules('ru-RU');
    const pairs = {one: 'пара', few: 'пары', many: 'пар', other: 'пары'};
    const variants = {one: 'вариант', few: 'варианта', many: 'вариантов', other: 'варианта'};
    const amount = (value, names) => numbers.format(value) + ' ' + names[plurals.select(value)];
    function calculate() {
      if (!form.checkValidity()) {
        result.textContent = 'Введите целые числа в каждом поле. Размеров — от 1 до 30, цветов — от 1 до 100, пар — от 1 до 10 000.';
        return;
      }
      const {sizes, colours, depth} = form.elements;
      const variantsCount = sizes.valueAsNumber * colours.valueAsNumber;
      const perColour = sizes.valueAsNumber * depth.valueAsNumber;
      const headline = document.createElement('strong');
      headline.textContent = amount(variantsCount * depth.valueAsNumber, pairs);
      const summary = document.createElement('p');
      summary.append('Объём партии — ', headline, '. Всего ' + amount(variantsCount, variants) + ' по размеру и цвету.');
      const extra = document.createElement('p');
      extra.textContent = 'Запас на каждый дополнительный цвет — ' + amount(perColour, pairs) + '.';
      result.replaceChildren(summary, extra);
    }
    form.hidden = false;
    form.addEventListener('submit', event => event.preventDefault());
    form.addEventListener('input', calculate);
    calculate();
  }

  const storagePrefix = 'tonko-five-wears.v1.';
  const photoKeys = ['before', 'after'];
  const photoLabels = {before: 'До первой носки', after: 'После пятой носки'};
  const validPhoto = value => typeof value === 'string' && value.startsWith('data:image/jpeg;base64,');

  async function readPhoto(file) {
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) throw Error('Выберите фотографию в формате JPEG, PNG или WebP.');
    const objectURL = URL.createObjectURL(file);
    try {
      const image = new Image();
      image.src = objectURL;
      try { await image.decode(); } catch { throw Error('Не удалось прочитать фотографию. Выберите другой файл.'); }
      const ratio = Math.min(1, 1100 / Math.max(image.naturalWidth, image.naturalHeight));
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(image.naturalWidth * ratio));
      canvas.height = Math.max(1, Math.round(image.naturalHeight * ratio));
      const context = canvas.getContext('2d');
      context.fillStyle = '#fff';
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      const data = canvas.toDataURL('image/jpeg', .8);
      if (!validPhoto(data)) throw Error('Не удалось подготовить фотографию. Попробуйте другой файл.');
      return data;
    } finally {
      URL.revokeObjectURL(objectURL);
    }
  }

  function exportDiary(form, photos) {
    const doc = document.implementation.createHTMLDocument('ТОНКО · После пяти носок');
    doc.documentElement.lang = 'ru';
    const charset = doc.createElement('meta');
    charset.setAttribute('charset', 'utf-8');
    doc.head.prepend(charset);
    const style = doc.createElement('style');
    style.textContent = 'body{font:17px/1.6 system-ui;margin:2rem auto;padding:0 1rem;max-width:46rem}h2{margin-top:2rem}img{max-width:100%;height:auto}p{white-space:pre-wrap}figure{margin:1rem 0}';
    doc.head.append(style);
    function line(tag, content) {
      const element = doc.createElement(tag);
      element.textContent = content;
      doc.body.append(element);
    }
    const value = key => form.elements.namedItem(key).value.trim();
    line('h1', 'После пяти носок');
    if (value('pair')) line('p', value('pair'));
    for (let day = 1; day <= 5; day++) {
      line('h2', 'Носка ' + day);
      for (const [key, label] of [['date','Дата'], ['shoes','Обувь'], ['wash','Стирка'], ['note','Наблюдение']]) {
        const answer = value(key + '-' + day);
        if (answer) line('p', label + ' — ' + answer);
      }
    }
    for (const key of photoKeys) {
      if (!validPhoto(photos[key])) continue;
      const figure = doc.createElement('figure');
      const photo = doc.createElement('img');
      photo.src = photos[key];
      photo.alt = photoLabels[key];
      const caption = doc.createElement('figcaption');
      caption.textContent = photoLabels[key];
      figure.append(photo, caption);
      doc.body.append(figure);
    }
    const url = URL.createObjectURL(new Blob(['<!doctype html>\n', doc.documentElement.outerHTML], {type: 'text/html;charset=utf-8'}));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'tonko-five-wears.html';
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 10000);
  }

  function initDiary() {
    const form = document.getElementById('wear-form');
    if (!form) return;
    const fields = Array.from(form.querySelectorAll('[name]'));
    const status = document.getElementById('wear-status');
    const photos = {};
    const revisions = {before: 0, after: 0};
    const unsaved = new Set();
    const pendingPhotos = new Set();
    const exportButton = document.getElementById('wear-export');
    const progress = document.getElementById('wear-progress');
    const counter = document.getElementById('wear-count');
    let unavailable = false;

    function write(key, value) {
      try {
        if (value) localStorage.setItem(storagePrefix + key, value);
        else localStorage.removeItem(storagePrefix + key);
        unsaved.delete(key);
        unavailable = false;
      } catch {
        unsaved.add(key);
      }
    }
    function read(key) {
      try { return localStorage.getItem(storagePrefix + key) || ''; }
      catch { unavailable = true; return ''; }
    }
    function report(message) {
      if (unavailable || unsaved.size) message = 'Браузеру не удалось сохранить все изменения. Скачайте дневник, пока страница открыта.';
      if (status.textContent !== message) status.textContent = message;
    }
    function updateProgress() {
      let complete = 0;
      for (let day = 1; day <= 5; day++) {
        const entry = key => form.elements.namedItem(key + '-' + day).value.trim();
        const full = Boolean(entry('date') && entry('note'));
        const partial = ['date', 'shoes', 'wash', 'note'].some(key => entry(key));
        document.getElementById('day-state-' + day).textContent = full ? 'Заполнено' : partial ? 'Черновик' : 'Без записи';
        if (full) complete++;
      }
      progress.value = complete;
      counter.textContent = 'Заполнено ' + complete + ' из 5';
    }
    function showPhoto(key, value) {
      photos[key] = validPhoto(value) ? value : '';
      const preview = form.querySelector('[data-preview="' + key + '"]');
      preview.hidden = !photos[key];
      if (photos[key]) preview.src = photos[key];
      else preview.removeAttribute('src');
      form.querySelector('[data-remove-photo="' + key + '"]').hidden = !photos[key];
    }
    function finishPhoto(key) {
      pendingPhotos.delete(key);
      exportButton.disabled = pendingPhotos.size > 0;
    }
    function restore() {
      fields.forEach(field => { field.value = read(field.name); });
      photoKeys.forEach(key => showPhoto(key, read(key)));
      updateProgress();
    }
    restore();
    form.hidden = false;
    report('Записи сохраняются автоматически.');
    form.addEventListener('submit', event => event.preventDefault());
    form.addEventListener('input', event => {
      const field = event.target;
      if (!field.name) return;
      write(field.name, field.value);
      updateProgress();
      report('Записи сохранены в этом браузере.');
    });
    for (const key of photoKeys) {
      const input = form.querySelector('[data-wear-photo="' + key + '"]');
      input.addEventListener('change', async () => {
        const file = input.files[0];
        if (!file) return;
        const revision = ++revisions[key];
        pendingPhotos.add(key);
        exportButton.disabled = true;
        try {
          const data = await readPhoto(file);
          if (revision !== revisions[key]) return;
          showPhoto(key, data);
          write(key, data);
          report('Фотография добавлена в дневник.');
        } catch (error) {
          if (revision === revisions[key]) report(error.message);
        } finally {
          if (revision === revisions[key]) { input.value = ''; finishPhoto(key); }
        }
      });
      form.querySelector('[data-remove-photo="' + key + '"]').addEventListener('click', () => {
        revisions[key]++;
        finishPhoto(key);
        input.value = '';
        showPhoto(key, '');
        write(key, '');
        report('Фотография убрана.');
        input.focus();
      });
    }
    exportButton.addEventListener('click', () => exportDiary(form, photos));
    document.getElementById('wear-clear').addEventListener('click', () => {
      const populated = fields.some(field => field.value) || photoKeys.some(key => photos[key]) || pendingPhotos.size;
      if (populated && !window.confirm('Очистить записи и фотографии этой пары? Перед этим можно скачать дневник.')) return;
      fields.forEach(field => { field.value = ''; write(field.name, ''); });
      photoKeys.forEach(key => { revisions[key]++; finishPhoto(key); showPhoto(key, ''); write(key, ''); });
      form.reset();
      form.querySelectorAll('.diary-day').forEach((item, index) => { item.open = index === 0; });
      updateProgress();
      report('Можно начинать дневник следующей пары.');
      form.elements.namedItem('pair').focus();
    });
    window.addEventListener('storage', event => {
      if (event.key === null) { restore(); return; }
      if (!event.key.startsWith(storagePrefix)) return;
      const key = event.key.slice(storagePrefix.length);
      const value = read(key);
      if (photoKeys.includes(key)) {
        revisions[key]++;
        finishPhoto(key);
        showPhoto(key, value);
      } else {
        const field = fields.find(item => item.name === key);
        if (!field) return;
        field.value = value;
        updateProgress();
      }
      unsaved.delete(key);
      report('Дневник обновлён в другой вкладке.');
    });
  }

  initArchive();
  initBatch();
  initDiary();
})();
