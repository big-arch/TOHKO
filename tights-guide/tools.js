(() => {
  const brands = window.BRAND_DATA || [];
  const business = window.BUSINESS_DATA || [];
  const photos = window.PHOTO_DATA || [];
  const favoriteKey = 'denie-favorites-v1';
  const getFavorites = () => {
    try { return JSON.parse(localStorage.getItem(favoriteKey) || '[]'); } catch { return []; }
  };
  const saveFavorites = (items) => {
    try { localStorage.setItem(favoriteKey, JSON.stringify(items)); } catch {}
    dispatchEvent(new CustomEvent('denie:favorites'));
  };
  const modelId = (brandSlug, index) => `${brandSlug}:${index}`;
  const allModels = brands.flatMap((item) => item.models.map((model, index) => ({ ...model, brand: item.name, slug: item.slug, status: item.status, id: modelId(item.slug,index), link: `brand.html?brand=${item.slug}` })));
  const favoriteButton = (item) => `<button class="favorite-button ${getFavorites().some((saved) => saved.id === item.id) ? 'active' : ''}" type="button" data-save-model="${item.id}">${getFavorites().some((saved) => saved.id === item.id) ? 'Сохранено' : 'В избранное'}</button>`;

  function toggleModel(id) {
    const model = allModels.find((item) => item.id === id);
    if (!model) return;
    const saved = getFavorites();
    const exists = saved.some((item) => item.id === id);
    const next = exists ? saved.filter((item) => item.id !== id) : [...saved, { id:model.id, brand:model.brand, name:model.name, den:model.den, link:model.link, url:model.url }];
    saveFavorites(next);
    document.querySelectorAll(`[data-save-model="${CSS.escape(id)}"]`).forEach((button) => {
      button.classList.toggle('active', !exists);
      button.textContent = exists ? 'В избранное' : 'Сохранено';
    });
  }

  function toggleBrand(slug) {
    const item = brands.find((entry) => entry.slug === slug);
    if (!item) return;
    const id = `brand:${slug}`;
    const saved = getFavorites();
    const exists = saved.some((entry) => entry.id === id);
    const next = exists ? saved.filter((entry) => entry.id !== id) : [...saved,{ id, brand:item.name, name:'Карточка бренда', den:null, link:`brand.html?brand=${slug}`, url:item.official }];
    saveFavorites(next);
    document.querySelectorAll(`[data-save-brand="${CSS.escape(slug)}"]`).forEach((button) => {
      button.classList.toggle('active', !exists);
      button.textContent = exists ? 'Сохранить бренд' : 'Бренд сохранён';
    });
  }

  document.addEventListener('click', (event) => {
    const modelButton = event.target.closest('[data-save-model]');
    if (modelButton) toggleModel(modelButton.dataset.saveModel);
    const brandButton = event.target.closest('[data-save-brand]');
    if (brandButton) toggleBrand(brandButton.dataset.saveBrand);
  });

  function initFavoriteButtons() {
    const detail = document.querySelector('[data-brand-detail]');
    if (detail) {
      const slug = new URLSearchParams(location.search).get('brand');
      const item = brands.find((entry) => entry.slug === slug) || brands[0];
      if (item) {
        const aside = detail.querySelector('.portal-brand-aside');
        if (aside && !aside.querySelector('[data-save-brand]')) {
          const button = document.createElement('button');
          button.type = 'button';
          button.className = 'favorite-button';
          button.dataset.saveBrand = item.slug;
          button.style.marginTop = '12px';
          aside.appendChild(button);
          button.textContent = getFavorites().some((entry) => entry.id === `brand:${item.slug}`) ? 'Бренд сохранён' : 'Сохранить бренд';
          button.classList.toggle('active', getFavorites().some((entry) => entry.id === `brand:${item.slug}`));
        }
        document.querySelectorAll('#brand-models tr').forEach((row) => {
          const link = row.querySelector('a[href]');
          if (!link || row.querySelector('[data-save-model]')) return;
          const model = item.models.find((entry) => link.href.endsWith(entry.url));
          if (!model) return;
          const index = item.models.indexOf(model);
          const cell = row.querySelector('td');
          cell.insertAdjacentHTML('beforeend', `<br>${favoriteButton({ ...model, id:modelId(item.slug,index) })}`);
        });
      }
    }
    const catalog = document.getElementById('brand-catalog-grid');
    if (catalog) {
      const addButtons = () => {
        catalog.querySelectorAll('.portal-catalog-card').forEach((card) => {
          if (card.querySelector('[data-save-brand]')) return;
          const link = card.querySelector('h2 a[href]');
          if (!link) return;
          const slug = new URL(link.href).searchParams.get('brand');
          const actions = card.querySelector('.portal-card-actions');
          if (!slug || !actions) return;
          const saved = getFavorites().some((entry) => entry.id === `brand:${slug}`);
          actions.insertAdjacentHTML('beforeend', `<button class="favorite-button ${saved ? 'active' : ''}" type="button" data-save-brand="${slug}">${saved ? 'Сохранён' : 'Сохранить'}</button>`);
        });
      };
      addButtons();
      new MutationObserver(addButtons).observe(catalog,{ childList:true });
    }
  }

  function initModelCompare() {
    const first = document.getElementById('model-a');
    const second = document.getElementById('model-b');
    if (!first || !second) return;
    const options = allModels.map((item) => `<option value="${item.id}">${item.brand} · ${item.name} · ${item.den ? item.den[0] === item.den[1] ? `${item.den[0]} DEN` : `${item.den[0]}–${item.den[1]} DEN` : 'без DEN'}</option>`).join('');
    first.innerHTML = options;
    second.innerHTML = options;
    first.value = 'wolford:0';
    second.value = 'falke:1';
    const table = document.getElementById('model-compare-table');
    const render = () => {
      const a = allModels.find((item) => item.id === first.value);
      const b = allModels.find((item) => item.id === second.value);
      if (!a || !b) return;
      const den = (value) => !value ? 'Не заявлен' : value[0] === value[1] ? `${value[0]} DEN` : `${value[0]}–${value[1]} DEN`;
      const cell = (item) => `<td><strong>${item.brand}</strong><br><a class="tool-link" href="${item.url}" target="_blank" rel="noopener">${item.name}</a><br>${favoriteButton(item)}</td>`;
      table.innerHTML = `<thead><tr><th>Критерий</th>${cell(a)}${cell(b)}</tr></thead><tbody><tr><td>Плотность</td><td>${den(a.den)}</td><td>${den(b.den)}</td></tr><tr><td>Назначение</td><td>${a.use}</td><td>${b.use}</td></tr><tr><td>Документированные свойства</td><td>${a.features}</td><td>${b.features}</td></tr><tr><td>Тип источника</td><td>${a.sourceType === 'retail' ? 'Розничный' : 'Официальный'}</td><td>${b.sourceType === 'retail' ? 'Розничный' : 'Официальный'}</td></tr></tbody>`;
    };
    first.addEventListener('change',render);
    second.addEventListener('change',render);
    render();
  }

  function renderSaved() {
    const list = document.getElementById('saved-list');
    if (!list) return;
    const saved = getFavorites();
    const count = document.getElementById('saved-count');
    if (count) count.textContent = `${saved.length} сохранено`;
    list.innerHTML = saved.length ? saved.map((item) => `<article class="saved-item"><div><h3>${item.brand}</h3><p>${item.name}${item.den ? ` · ${item.den[0]} DEN` : ''}</p></div><div class="tool-actions"><a class="tool-link" href="${item.link}">Открыть</a><button class="favorite-button" type="button" data-remove-saved="${item.id}">Удалить</button></div></article>`).join('') : '<div class="saved-empty"><h3>Список пока пуст</h3><p>Добавьте модель из сравнения или бренд из каталога. Данные останутся только на этом устройстве.</p><a class="portal-button portal-button-primary" href="compare.html">Выбрать модели</a></div>';
    list.querySelectorAll('[data-remove-saved]').forEach((button) => button.addEventListener('click', () => saveFavorites(getFavorites().filter((item) => item.id !== button.dataset.removeSaved))));
  }

  function initWardrobe() {
    const outfit = document.getElementById('outfit-form');
    if (outfit) {
      outfit.addEventListener('submit',(event) => {
        event.preventDefault();
        const weather = document.getElementById('outfit-weather').value;
        const occasion = document.getElementById('outfit-occasion').value;
        const look = document.getElementById('outfit-look').value;
        const base = { warm:12,mild:40,cold:80,frost:140 }[weather] + { office:0,evening:-5,active:10,travel:0 }[occasion] + { natural:-10,matte:15,color:10 }[look];
        const candidates = allModels.filter((item) => item.den && item.status !== 'medical' && item.status !== 'archive').sort((a,b) => Math.abs((a.den[0]+a.den[1])/2-base)-Math.abs((b.den[0]+b.den[1])/2-base));
        const unique = [...new Map(candidates.map((item) => [item.slug,item])).values()].slice(0,3);
        document.getElementById('outfit-result').innerHTML = `<h3>Ваши три варианта</h3><p>Ориентир: около ${Math.max(5,base)} DEN. Это редакционный подбор по плотности, а не гарантия посадки или наличия.</p><div class="tool-result-list">${unique.map((item) => `<article class="tool-model-result"><h3>${item.brand} · ${item.name}</h3><p>${item.den[0]} DEN · ${item.use}</p><div class="tool-actions"><a class="tool-link" href="${item.url}" target="_blank" rel="noopener">Карточка и источник</a>${favoriteButton(item)}</div></article>`).join('')}</div>`;
      });
    }
    const snag = document.getElementById('snag-size-form');
    if (snag) {
      const curvy = [['A/B','A/B','C'],['C','C','D'],['D','D','E'],['E','E','F'],['Short F','F','G'],['Short F','F','G'],['G','G','G']];
      const athletic = [['A/B','A/B','A/B'],['A/B','A/B','C'],['C','C','D'],['D','D','E'],['E','E','F'],['Short F','F','G'],['G','G','G']];
      snag.addEventListener('submit',(event) => {
        event.preventDefault();
        const size = Number(document.getElementById('snag-clothes').value);
        const height = document.getElementById('snag-height').value;
        const shape = document.getElementById('snag-shape').value;
        const result = (shape === 'curvy' ? curvy : athletic)[size][height];
        document.getElementById('snag-size-result').innerHTML = `<h3>Размер Snag: ${result}</h3><p>Расчёт по официальной таблице Curvilicious или Athletic. Перед заказом проверьте актуальную таблицу производителя.</p><a class="tool-link" href="https://snagtights.com/pages/size-guide-tights" target="_blank" rel="noopener">Официальная таблица Snag</a>`;
      });
    }
    const cost = document.getElementById('cost-form');
    if (cost) {
      cost.addEventListener('submit',(event) => {
        event.preventDefault();
        if (!cost.reportValidity()) return;
        const price = Number(document.getElementById('cost-price').value);
        const wears = Number(document.getElementById('cost-wears').value);
        document.getElementById('cost-result').innerHTML = `<h3>${(price/wears).toFixed(2)} ₽ за носку</h3><p>Это простой расчёт цены делённой на введённое число использований, а не прогноз срока службы.</p>`;
      });
    }
    renderSaved();
    addEventListener('denie:favorites',renderSaved);
  }

  function initAtlas() {
    const tones = {
      porcelain:['Фарфоровый и холодный','Ищите нейтральные или слегка розоватые оттенки без оранжевого подтона. Сравнивайте при дневном свете.'],
      neutral:['Светлый нейтральный','Начните с естественного бежа без выраженного блеска. Сверяйте цвет с открытой кожей рук и шеи.'],
      warm:['Тёплый и золотистый','Подойдут тёплые бежевые и бронзовые оттенки без чрезмерной желтизны.'],
      olive:['Оливковый','Ищите нейтральные или слегка сероватые оттенки. Слишком розовый беж может выглядеть контрастно.'],
      tan:['Смуглый','Глубокие бронзовые и коричневые оттенки обычно гармоничнее светлого бежа.'],
      deep:['Глубокий тёмный','Выбирайте глубокий коричневый, кофейный или дымчатый цвет, сохраняющий естественный вид кожи.']
    };
    document.querySelectorAll('[data-tone]').forEach((button) => button.addEventListener('click',() => {
      document.querySelectorAll('[data-tone]').forEach((item) => item.classList.toggle('active',item === button));
      const data = tones[button.dataset.tone];
      const result = document.getElementById('atlas-result');
      result.innerHTML = `<h3>${data[0]}</h3><p>${data[1]}</p><p>Экран не передаёт цвет абсолютно точно. Используйте рекомендацию как направление, а не как колориметрическое измерение.</p>`;
      result.style.borderTop = `16px solid ${button.dataset.color}`;
    }));
    const issues = {
      slip:['Сползает вниз','Проверьте рост, талию и ширину пояса. Избыток длины или слабый пояс может быть причиной. Не выбирайте автоматически меньший размер.'],
      knee:['Складки на коленях','Возможны избыток длины или слабое возвращение формы. Сравните рост по таблице и эластичность конкретной модели.'],
      toe:['Давит мысок','Проверьте длину стопы и размер. Не растягивайте ткань силой. При боли прекратите носку.'],
      waist:['Врезается пояс','Ищите широкий мягкий пояс или другой крой. Сильное давление не является нормой.'],
      ladder:['Появилась затяжка','Проверьте контакт с ногтями и украшениями. Лак лишь временно ограничивает повреждение, но не восстанавливает полотно.'],
      static:['Ткань электризуется','Проверьте состав, влажность воздуха и сочетание с одеждой. Следуйте уходу производителя и не используйте агрессивную химию.']
    };
    document.querySelectorAll('[data-fit-issue]').forEach((button) => button.addEventListener('click',() => {
      const data = issues[button.dataset.fitIssue];
      const result = document.getElementById('fit-result');
      result.innerHTML = `<h3>${data[0]}</h3><p>${data[1]}</p>`;
      result.classList.add('active');
    }));
  }

  function initSearch() {
    const input = document.getElementById('global-search');
    if (!input) return;
    const type = document.getElementById('search-type');
    const count = document.getElementById('search-count');
    const results = document.getElementById('search-results');
    const pages = [
      ['Журнал ТОНКО','Свет, рисунки, конструкция, производство и история; маршруты чтения','journal.html','Журнал'],
      ['Под лупой','Увеличение фотографий, блеск, кружево и сравнение фактур','textures.html','Интерактив'],
      ['Капрон, нейлон и полиамид','Материалы, волокна, эластан и состав колготок','nylon.html','Гид'],
      ['Источники и авторы','Проверка истории брендов, фотографии и логотипы','sources.html','Раздел'],
      ['Бренды и модели','Каталог компаний, плотностей и источников','brands.html','Раздел'],
      ['Легинсы, тайтсы и колготки','Отличия, GSM, спорт и мужской крой','leggings.html','Гид'],
      ['Люди и экономика индустрии','Бизнес-кейсы, выручка и бизнес-модели','business.html','Бизнес'],
      ['Мужчины в колготках','Анатомия, посадка, спорт, сцена и стиль','men.html','Гид'],
      ['Как выбрать: мастерская','Подбор пары, сравнение DEN, викторина, конструкция и уход','guide.html','Гид'],
      ['История колготок','Нейлон, эластан, мода и технологии','history.html','История'],
      ['Фотогалерея','Каталожные фотографии, мужские образы, фактура и происхождение изображений','lookbook.html','Фото'],
      ['Фетиш: психология и психофизиология','Восприятие, ассоциации, интерес и расстройство, согласие и отношения','fetish.html','18+']
    ];
    const entries = [
      ...(window.TONKO_JOURNAL || []).map(s=>({title:s.title,text:s.description+' '+s.short+' '+s.theme,url:s.url,kind:'Журнал'})),
      ...pages.map(([title,text,url,kind]) => ({title,text,url,kind})),
      ...brands.map((item) => ({title:item.name,text:`${item.summary} ${item.models.map((model) => model.name).join(' ')}`,url:`brand.html?brand=${item.slug}`,kind:'Бренд'})),
      ...business.map((item) => ({title:`${item.name} · ${item.company}`,text:`${item.story} ${item.figure}`,url:`business.html#profile-${item.id}`,kind:'Бизнес'})),
      ...photos.map((item) => ({title:item.title,text:`${item.caption} ${item.author}`,url:`lookbook.html#photo-${item.id}`,kind:'Фото'}))
    ];
    const render = () => {
      const query = input.value.trim().toLowerCase();
      const list = entries.filter((entry) => (type.value === 'all' || entry.kind === type.value) && (!query || `${entry.title} ${entry.text}`.toLowerCase().includes(query))).slice(0,40);
      count.textContent = query ? `Найдено ${list.length} результатов` : `Популярные материалы и страницы`;
      results.innerHTML = list.map((entry) => `<a class="search-result" href="${entry.url}"><span class="portal-chip">${entry.kind}</span><h2>${entry.title}</h2><p>${entry.text.length > 240 ? `${entry.text.slice(0,240)}…` : entry.text}</p><span class="tool-link">Открыть материал <i class="ph ph-arrow-right" aria-hidden="true"></i></span></a>`).join('');
    };
    input.addEventListener('input',render);
    type.addEventListener('change',render);
    const query = new URLSearchParams(location.search).get('q');
    if (query) input.value = query;
    render();
  }

  function initSuggestion() {
    const form = document.getElementById('suggest-form');
    if (!form) return;
    form.addEventListener('submit',(event) => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const name = document.getElementById('suggest-brand').value.trim();
      const model = document.getElementById('suggest-model').value.trim();
      const url = document.getElementById('suggest-url').value.trim();
      const note = document.getElementById('suggest-note').value.trim();
      const text = `# Предложение для каталога ТОНКО\n\nБренд: ${name}\nМодель: ${model || 'Не указана'}\nИсточник: ${url}\nПримечание: ${note || 'Нет'}\n\nПредложение подготовлено локально и не отправлено автоматически.`;
      document.getElementById('suggest-result').hidden = false;
      document.getElementById('suggest-preview').textContent = text;
      const download = document.getElementById('suggest-download');
      download.onclick = () => {
        const blobUrl = URL.createObjectURL(new Blob([text],{type:'text/markdown;charset=utf-8'}));
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = 'denie-predlozhenie.md';
        link.click();
        URL.revokeObjectURL(blobUrl);
      };
    });
  }

  initFavoriteButtons();
  initModelCompare();
  initWardrobe();
  initAtlas();
  initSearch();
  initSuggestion();
})();
