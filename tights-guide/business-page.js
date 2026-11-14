(() => {
  const data = window.BUSINESS_DATA || [];
  const grid = document.getElementById('business-grid');
  if (!grid) return;
  const search = document.getElementById('business-search');
  const count = document.getElementById('business-count');
  const empty = document.getElementById('business-empty');
  const filters = [...document.querySelectorAll('[data-business-filter]')];
  let category = 'all';

  const render = () => {
    const needle = search.value.trim().toLowerCase();
    const list = data.filter((item) => {
      const matchesText = !needle || `${item.name} ${item.company} ${item.model} ${item.story}`.toLowerCase().includes(needle);
      const matchesCategory = category === 'all' || category === 'wealth' && item.figureType.includes('состоян') || category === 'revenue' && /выручка|оборот/i.test(item.figureType) || category === 'history' && item.figureType.includes('Год основания');
      return matchesText && matchesCategory;
    });
    count.textContent = `Показано ${list.length} из ${data.length} бизнес-кейсов`;
    empty.hidden = list.length > 0;
    grid.innerHTML = list.map((item) => `
      <article class="business-profile" id="profile-${item.id}">
        <div class="business-profile-photo"><img src="${item.image}" alt="${item.alt}" loading="lazy"><span>${item.company}</span></div>
        <div class="business-profile-body"><p class="portal-eyebrow">${item.role}</p><h2>${item.name}</h2><p class="business-profile-company">${item.company}</p><div class="business-profile-model"><strong>Бизнес-модель:</strong><br>${item.model}</div><div class="business-figure"><strong>${item.figure}</strong><span>${item.figureType}</span></div><p>${item.story}</p><details><summary>Разбор решения и финансовый контекст</summary><p>${item.lesson}</p><p>${item.extra}</p><p><a class="tool-link" href="${item.source}" target="_blank" rel="noopener">Основной источник <i class="ph ph-arrow-square-out" aria-hidden="true"></i></a> · <a class="tool-link" href="${item.extraSource}" target="_blank" rel="noopener">Дополнительный источник <i class="ph ph-arrow-square-out" aria-hidden="true"></i></a></p></details><p class="photo-credit">${item.caption}<br>Фото: ${item.author} · <a href="${item.licenseUrl}" target="_blank" rel="noopener">${item.license}</a> · <a href="${item.imageSource}" target="_blank" rel="noopener">Источник изображения</a> · Веб версия уменьшена</p></div>
      </article>`).join('');
  };
  search.addEventListener('input', render);
  filters.forEach((button) => button.addEventListener('click', () => {
    category = button.dataset.businessFilter;
    filters.forEach((item) => {
      item.classList.toggle('active', item === button);
      item.setAttribute('aria-pressed', String(item === button));
    });
    render();
  }));
  render();
})();
