const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

// Toast Notification
const toast = $('#toast');
let toastTimer;
function showToast(message) {
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('visible');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('visible'), 3200);
}

// Mobile Menu Navigation
const mobileToggle = $('#mobile-toggle');
const mainNav = $('.main-nav');
if (mobileToggle && mainNav) {
  mobileToggle.addEventListener('click', () => {
    const isHidden = window.getComputedStyle(mainNav).display === 'none';
    mainNav.style.display = isHidden ? 'flex' : 'none';
    if (isHidden) {
      mainNav.style.flexDirection = 'column';
      mainNav.style.position = 'absolute';
      mainNav.style.top = '100%';
      mainNav.style.left = '0';
      mainNav.style.right = '0';
      mainNav.style.background = 'rgba(248, 245, 238, 0.98)';
      mainNav.style.padding = '24px';
      mainNav.style.borderBottom = '1px solid var(--border)';
    }
  });
}

/* ==========================================================================
   PHOTO GALLERY DATA (LOOKBOOK.HTML & HOME)
   ========================================================================== */
const galleryData = [
  {
    id: 'gal-1',
    category: 'women',
    title: 'Городской стритстайл: полупрозрачные 20 DEN',
    model: 'Wolford Individual 20 / Falke Pure Matt 20',
    den: '20 DEN',
    image: 'assets/images/woman-sheer-street.jpg',
    desc: 'Классический городской лук: элегантные черные 20 DEN с легким шелковистым финишем в сочетании с бежевым тренчем и туфлями на шпильке. Колготки выравнивают тон ноги и подчеркивают линию обуви.',
    tip: 'Для дневного света выбирайте матовые или слегка сатиновые колготки без жирного глянцевого отблеска.'
  },
  {
    id: 'gal-2',
    category: 'women',
    title: 'Осенний монохром: матовая микрофибра 60 DEN',
    model: 'Calzedonia Soft Microfibra 50 / Omsa Velour 70',
    den: '60 DEN',
    image: 'assets/images/woman-opaque-fashion.jpg',
    desc: 'Глубокий матовый черный цвет без полос и просветов. Плотная микрофибра 3D визуально вытягивает силуэт и прекрасно рифмуется с шерстяной юбкой, объемным свитером и грубыми ботильонами.',
    tip: 'Матовые непрозрачные колготки гармонично смотрятся с фактурными тканями: твидом, кашемиром, кожей и замшей.'
  },
  {
    id: 'gal-3',
    category: 'women',
    title: 'Парижский шик: фантазийный горошек Plumetis',
    model: 'Calzedonia Polka Dot / Gerbe Plumetis',
    den: '20 DEN',
    image: 'assets/images/woman-polka-dots.jpg',
    desc: 'Мелкий горох на прозрачном шелковистом фоне. Нестареющий стилистический прием, оживляющий простое маленькое черное платье или оверсайз жакет с туфлями Мэри Джейн.',
    tip: 'Чем мельче шаг горошка, тем изящнее и универсальнее образ. Крупный принт визуально расширяет объем голени.'
  },
  {
    id: 'gal-4',
    category: 'men',
    title: 'Мужской стритвир: черные колготки под свободные шорты',
    model: 'Activskin A60 / Falke Ergonomic Men',
    den: '60–80 DEN',
    image: 'assets/images/men-meggings.jpg',
    desc: 'Современный городской аутфит: плотные матовые мужские колготки (меггинсы) в многослойном образе со свободными темными шортами, худи и массивными кроссовками.',
    tip: 'В мужском стайлинге ключевое правило — глубокая матовая текстура полотна: она воспринимается как технологичная ткань спортивного стиля.'
  },
  {
    id: 'gal-5',
    category: 'men',
    title: 'Мужская посадка и базовый слой',
    model: 'Adrian Men Mister 40 / Wolford Men Care',
    den: '40 DEN',
    image: 'assets/images/man-tights-real.jpg',
    desc: 'Реальная посадка мужских капроновых колготок: анатомический крой, комфортная резинка на талии без сдавливания и свобода движений.',
    tip: 'Под зауженные брюки и костюмы в холодное время тонкие колготки 40–60 DEN подходят лучше громоздких термокальсон, не собираясь складками на коленях.'
  },
  {
    id: 'gal-6',
    category: 'texture',
    title: 'Анатомический крой торса и плоские швы',
    model: 'Студийный рентген конструкции колготок',
    den: '15–40 DEN',
    image: 'assets/images/sheer-panty-detail.jpg',
    desc: 'Наглядная разница между прозрачной зоной ноги и усиленным анатомическим поясом. Плоские швы соединяются встык (flatlock), не натирая кожу и не выделяясь под обтягивающей одеждой.',
    tip: 'Хлопковая ластовица — обязательный маркер качественной пары. Она гарантирует гигиену и воздухопроницаемость.'
  },
  {
    id: 'gal-7',
    category: 'texture',
    title: 'Макро-структура полиамидной нити',
    model: 'Эластан двойной обкрутки (Double Covered)',
    den: '15 DEN',
    image: 'assets/images/sample-pantyhose-texture.jpg',
    desc: 'Крупный план переплетения нитей под натяжением: равномерная петлевая структура без дефектов и полос. Высококачественная нить возвращается в исходную форму после растяжения.',
    tip: 'Технология двойной обкрутки (две нити полиамида спирально оплетают эластановую сердцевину) многократно повышает стойкость к стрелкам.'
  },
  {
    id: 'gal-8',
    category: 'texture',
    title: 'Моделирующий торс Control-Top',
    model: 'Зонированная коррекция живота и бедер',
    den: '40–70 DEN',
    image: 'assets/images/control-top-panty.jpg',
    desc: 'Плотные шортики с распределенной утяжкой: бережная фиксация талии, сглаживание боковых линий и поддержка ягодиц с постепенным переходом в эластичную ножку.',
    tip: 'Никогда не берите корректирующие колготки на размер меньше — это передавливает сосуды и приводит к скатыванию пояса.'
  }
];

function initGallery() {
  const galleryGrid = $('#gallery-grid');
  if (!galleryGrid) return;

  galleryGrid.innerHTML = galleryData.map((item) => `
    <article class="lookbook-item" data-category="${item.category}" data-id="${item.id}">
      <div class="lookbook-img-box">
        <img src="${item.image}" alt="${item.title}" loading="lazy" width="600" height="750">
        <span class="lookbook-badge">${item.den}</span>
      </div>
      <div class="lookbook-content">
        <span class="story-category" style="margin-bottom:4px;">${item.category === 'women' ? 'Девушки · Стиль' : item.category === 'men' ? 'Мужчинам · Стритвир' : 'Макро · Текстура'}</span>
        <h3>${item.title}</h3>
        <p>${item.desc}</p>
        <div class="lookbook-stylist-tip">
          <strong>Совет стилиста:</strong>
          ${item.tip}
        </div>
      </div>
    </article>
  `).join('');

  $$('.gallery-filter-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      $$('.gallery-filter-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      const cat = btn.dataset.galleryFilter;
      let count = 0;
      $$('.lookbook-item', galleryGrid).forEach((card) => {
        const match = cat === 'all' || card.dataset.category === cat;
        card.style.display = match ? 'flex' : 'none';
        if (match) count++;
      });
      const counter = $('#gallery-count');
      if (counter) counter.textContent = `Показано кадров: ${count} из ${galleryData.length}`;
    });
  });

  // Lightbox click
  $$('.lookbook-item', galleryGrid).forEach((card) => {
    card.addEventListener('click', () => {
      const item = galleryData.find((x) => x.id === card.dataset.id);
      if (item) openModalLightbox(item);
    });
  });
}

function openModalLightbox(item) {
  const overlay = $('#modal-overlay');
  const content = $('#modal-content');
  if (!overlay || !content) return;

  content.innerHTML = `
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:32px; align-items:center;">
      <div style="border-radius:12px; overflow:hidden; background:#000;">
        <img src="${item.image}" alt="${item.title}" style="width:100%; max-height:75vh; object-fit:contain;">
      </div>
      <div>
        <span class="tag-badge" style="margin-bottom:12px;">${item.den} · ${item.category.toUpperCase()}</span>
        <h2 style="font-family:var(--font-serif); font-size:28px; line-height:1.2; margin:0 0 12px 0;">${item.title}</h2>
        <p style="font-size:15px; line-height:1.6; color:var(--ink-muted); margin-bottom:20px;">${item.desc}</p>
        <div style="background:var(--bg-subtle); padding:16px; border-radius:8px; border-left:3px solid var(--wine);">
          <strong style="color:var(--wine); font-size:11px; text-transform:uppercase; letter-spacing:1px; display:block; margin-bottom:4px;">Стилистический нюанс:</strong>
          <span style="font-size:13px; color:#45403c;">${item.tip}</span>
        </div>
      </div>
    </div>
  `;
  overlay.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeModalLightbox() {
  const overlay = $('#modal-overlay');
  if (!overlay) return;
  overlay.classList.remove('active');
  document.body.style.overflow = '';
}

$('#modal-close')?.addEventListener('click', closeModalLightbox);
$('#modal-overlay')?.addEventListener('click', (e) => {
  if (e.target.id === 'modal-overlay') closeModalLightbox();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModalLightbox();
});

/* ==========================================================================
   COMPARATOR ON INDEX.HTML
   ========================================================================== */
const comparatorPresets = {
  '20den': [
    { brand: 'Wolford', model: 'Individual 20', den: 20, finish: 'Матовый шелк (zero streak)', snag: 4, comfort: 5, life: 'Высокая (до 2 лет)', price: 'Люкс (₽₽₽₽)', verdict: 'Мировой эталон равномерности плетения' },
    { brand: 'Falke', model: 'Pure Matt 20', den: 20, finish: 'Ультраматовый пудровый', snag: 4, comfort: 5, life: 'Высокая (до 2 лет)', price: 'Премиум (₽₽₽)', verdict: 'Истинный матовый без единого блика' },
    { brand: 'Conte', model: 'Prestige 20', den: 20, finish: 'Шелковистый с легким глянцем', snag: 4, comfort: 4, life: 'Средняя (сезон)', price: 'Доступный (₽)', verdict: 'Рекордная прочность за разумные деньги' }
  ],
  'matte': [
    { brand: 'Falke', model: 'Pure Matt 50', den: 50, finish: 'Глубокий матовый бархат', snag: 5, comfort: 5, life: 'Очень высокая (3+ года)', price: 'Премиум (₽₽₽)', verdict: 'Не вытягивается на коленях, 3D-микрофибра' },
    { brand: 'Pierre Mantoux', model: 'Veloutine 50', den: 50, finish: 'Кутюрный мягкий бархат', snag: 5, comfort: 5, life: 'Высокая', price: 'Люкс (₽₽₽₽)', verdict: 'Итальянский кутюр с двойной обкруткой лайкры' },
    { brand: 'Omsa', model: 'Velour 70', den: 70, finish: 'Плотный матовый бархат', snag: 5, comfort: 5, life: 'Высокая', price: 'Доступный (₽)', verdict: 'Идеальный глубокий черный цвет без блеска' }
  ],
  'men': [
    { brand: 'Adrian Men', model: 'Mister 40 Men', den: 40, finish: 'Матовый повседневный', snag: 5, comfort: 5, life: 'Высокая', price: 'Мидл (₽₽)', verdict: 'Анатомический мужской гульфик и удлиненная стопа' },
    { brand: 'Activskin', model: 'A60 Performance', den: 60, finish: 'Микронейлон технологичный', snag: 5, comfort: 5, life: 'Очень высокая', price: 'Премиум (₽₽₽)', verdict: 'Американский функционал для спорта и походов' },
    { brand: 'Wolford', model: 'Care & Men Support', den: 40, finish: 'Компрессионный матовый', snag: 5, comfort: 5, life: 'Максимальная', price: 'Люкс (₽₽₽₽)', verdict: 'Градуированная компрессия для вен и авиаперелетов' }
  ]
};

function renderMainComparator(presetKey) {
  const table = $('#comparator-main-table');
  if (!table) return;

  const data = comparatorPresets[presetKey] || comparatorPresets['20den'];

  table.innerHTML = `
    <thead>
      <tr style="background:var(--bg-subtle); border-bottom:1px solid var(--border);">
        <th style="padding:16px 20px;">Критерий</th>
        ${data.map((m) => `<th style="padding:16px 20px; font-size:16px; font-family:var(--font-serif); color:var(--wine); font-weight:700;">${m.brand}<br><span style="font-size:13px; font-family:var(--font-sans); color:var(--ink-primary); font-weight:600;">${m.model} (${m.den} DEN)</span></th>`).join('')}
      </tr>
    </thead>
    <tbody>
      <tr style="border-bottom:1px solid var(--border);"><td style="padding:14px 20px; font-weight:600;">Финиш полотна</td>${data.map((m) => `<td style="padding:14px 20px;">${m.finish}</td>`).join('')}</tr>
      <tr style="border-bottom:1px solid var(--border);"><td style="padding:14px 20px; font-weight:600;">Стойкость к затяжкам</td>${data.map((m) => `<td style="padding:14px 20px;">${'★'.repeat(m.snag)}${'☆'.repeat(5 - m.snag)}</td>`).join('')}</tr>
      <tr style="border-bottom:1px solid var(--border);"><td style="padding:14px 20px; font-weight:600;">Комфорт пояса и швов</td>${data.map((m) => `<td style="padding:14px 20px;">${'★'.repeat(m.comfort)}${'☆'.repeat(5 - m.comfort)}</td>`).join('')}</tr>
      <tr style="border-bottom:1px solid var(--border);"><td style="padding:14px 20px; font-weight:600;">Ресурс службы</td>${data.map((m) => `<td style="padding:14px 20px;">${m.life}</td>`).join('')}</tr>
      <tr style="border-bottom:1px solid var(--border);"><td style="padding:14px 20px; font-weight:600;">Ценовая категория</td>${data.map((m) => `<td style="padding:14px 20px;"><strong>${m.price}</strong></td>`).join('')}</tr>
      <tr><td style="padding:14px 20px; font-weight:600;">Вердикт редакции</td>${data.map((m) => `<td style="padding:14px 20px; color:var(--wine); font-weight:600;"><small>${m.verdict}</small></td>`).join('')}</tr>
    </tbody>
  `;
}

function initComparatorButtons() {
  $('#btn-comp-20')?.addEventListener('click', function() {
    $$('#comparator-section .filter-pill').forEach((b) => b.classList.remove('active'));
    this.classList.add('active');
    renderMainComparator('20den');
  });
  $('#btn-comp-matte')?.addEventListener('click', function() {
    $$('#comparator-section .filter-pill').forEach((b) => b.classList.remove('active'));
    this.classList.add('active');
    renderMainComparator('matte');
  });
  $('#btn-comp-men')?.addEventListener('click', function() {
    $$('#comparator-section .filter-pill').forEach((b) => b.classList.remove('active'));
    this.classList.add('active');
    renderMainComparator('men');
  });
  renderMainComparator('20den');
}

/* ==========================================================================
   DEN LAB SLIDER (GUIDE.HTML)
   ========================================================================== */
function initDenSlider() {
  const denSlider = $('#den-slider');
  if (!denSlider) return;

  const denValue = $('#den-value');
  const denTitle = $('#den-title');
  const denDescription = $('#den-description');
  const fabricLayer = $('#fabric-layer');

  const denRanges = [
    { max: 15, title: 'Ультрапрозрачные (5–15 DEN)', description: 'Тончайшая невесомая вуаль. Подходит для дресс-кода в жару, открытой обуви и деликатного выравнивания тона кожи.' },
    { max: 40, title: 'На каждый день (20–40 DEN)', description: 'Классический баланс прочности и прозрачности. Идеальны для офиса, прогулок и переменчивой демисезонной погоды.' },
    { max: 70, title: 'Плотные матовые (50–70 DEN)', description: 'Непрозрачный бархатистый матовый цвет из микрофибры 3D. Высокая устойчивость к затяжкам, комфортны осенью и весной.' },
    { max: 100, title: 'Тёплые плотные (80–100 DEN)', description: 'Надежная защита от холода. Создают глубокую цветную основу образа под пальто, твид и теплые юбки.' },
    { max: 300, title: 'Термоколготки (120–300 DEN)', description: 'Зимняя защита с кашемиром, микроплюшем или начёсом (термофлисом). Согревают в мороз ниже нуля.' }
  ];

  const update = () => {
    const val = Number(denSlider.value);
    const item = denRanges.find((x) => val <= x.max) || denRanges[denRanges.length - 1];
    if (denValue) denValue.textContent = val;
    if (denTitle) denTitle.textContent = item.title;
    if (denDescription) denDescription.textContent = item.description;
    if (fabricLayer) fabricLayer.style.opacity = String(0.04 + val / 180);
  };

  denSlider.addEventListener('input', update);
  update();
}

/* ==========================================================================
   NUDE ATLAS (GUIDE.HTML)
   ========================================================================== */
const nudeData = {
  porcelain: {
    name: 'Фарфоровый (очень светлая кожа)',
    color: '#faebd7',
    desc: 'Холодный фарфоровый подтон без желтизны. Главная опасность — купить стандартный беж, который будет выглядеть оранжевым пятном на бледной коже.',
    advice: 'Ищите ультратонкие модели 8–15 DEN без шиммера и с сероватым или розоватым холодным подтоном.',
    brands: [
      { brand: 'Wolford', shade: 'Fairly Light / Gobi', tone: '#f7ede2' },
      { brand: 'Falke', shade: 'Powder', tone: '#f8eee4' },
      { brand: 'Conte', shade: 'Natural / Shade', tone: '#f3e5d8' },
      { brand: 'Omsa', shade: 'Playa (светлый)', tone: '#f0e2d5' },
      { brand: 'Golden Lady', shade: 'Melon (очень легкий)', tone: '#f5e8da' }
    ]
  },
  neutral: {
    name: 'Светлый нейтральный беж',
    color: '#ecd7c2',
    desc: 'Универсальный европейский тон кожи. Подходит большинству в межсезонье и ранней весной.',
    advice: 'Откажитесь от оттенков со словом "Bronz" до появления естественного загара. Выбирайте натуральный пудровый матовый эффект.',
    brands: [
      { brand: 'Wolford', shade: 'Cosmetic', tone: '#ecd3be' },
      { brand: 'Falke', shade: 'Golden / Sand', tone: '#e8ceb7' },
      { brand: 'Conte', shade: 'Natural', tone: '#e6cbb4' },
      { brand: 'Omsa', shade: 'Daino / Playa', tone: '#e2c6ad' },
      { brand: 'Golden Lady', shade: 'Daino', tone: '#dfc2a8' }
    ]
  },
  golden: {
    name: 'Золотистый загар / Теплый беж',
    color: '#d8b998',
    desc: 'Теплый оттенок кожи с легким летним загаром или природным оливковым подтоном.',
    advice: 'Оттенок колготок должен точно совпадать с тоном открытых рук и шеи, иначе возникнет визуальный диссонанс.',
    brands: [
      { brand: 'Wolford', shade: 'Caramel', tone: '#d4ad88' },
      { brand: 'Falke', shade: 'Brazil / Sun', tone: '#cea47e' },
      { brand: 'Conte', shade: 'Bronz', tone: '#c79d76' },
      { brand: 'Omsa', shade: 'Caramello / Sierra', tone: '#c29770' },
      { brand: 'Golden Lady', shade: 'Castoro', tone: '#bf926b' }
    ]
  },
  dark: {
    name: 'Смуглый / Глубокий загар',
    color: '#b58e69',
    desc: 'Смуглая или сильно загорелая кожа. Светлые оттенки будут давать белесый "меловой" эффект на ногах.',
    advice: 'Выбирайте глубокие бронзовые, мокко или дымчато-графитовые оттенки, сохраняющие прозрачность.',
    brands: [
      { brand: 'Wolford', shade: 'Mocca / Bronze', tone: '#9c734e' },
      { brand: 'Falke', shade: 'Cocoon / Dark Navy', tone: '#926a47' },
      { brand: 'Conte', shade: 'Mocca', tone: '#8e6542' },
      { brand: 'Omsa', shade: 'Castagna', tone: '#885e3c' },
      { brand: 'Golden Lady', shade: 'Moka', tone: '#825938' }
    ]
  }
};

function initNudeAtlas() {
  const container = $('#nude-matrix-wrap');
  if (!container) return;

  function setTone(key) {
    const data = nudeData[key];
    if (!data) return;

    $$('.skin-tone-btn').forEach((b) => b.classList.toggle('active', b.dataset.tone === key));

    container.innerHTML = `
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:36px; padding:36px;">
        <div>
          <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
            <span style="display:inline-block; width:28px; height:28px; border-radius:50%; background:${data.color}; border:1px solid rgba(0,0,0,0.15);"></span>
            <h3 style="margin:0; font-family:var(--font-serif); font-size:26px;">${data.name}</h3>
          </div>
          <p style="font-size:14px; line-height:1.6; color:var(--ink-muted); margin-bottom:16px;">${data.desc}</p>
          <div style="background:var(--bg-subtle); padding:16px; border-radius:8px; border-left:3px solid var(--wine);">
            <strong style="font-size:11px; text-transform:uppercase; color:var(--wine); letter-spacing:1px; display:block; margin-bottom:4px;">Правило стилиста:</strong>
            <span style="font-size:13px; color:#494340;">${data.advice}</span>
          </div>
        </div>

        <div>
          <h4 style="font-family:var(--font-serif); font-size:20px; margin:0 0 16px 0;">Названия тонов у ведущих брендов</h4>
          <table style="width:100%; border-collapse:collapse; font-size:13px;">
            <thead>
              <tr style="border-bottom:1px solid var(--border); color:var(--ink-muted); text-transform:uppercase; font-size:11px;">
                <th style="padding:8px 0;">Бренд</th>
                <th style="padding:8px 0;">Официальный оттенок</th>
                <th style="padding:8px 0;">Свотч</th>
              </tr>
            </thead>
            <tbody>
              ${data.brands.map((b) => `
                <tr style="border-bottom:1px solid var(--border);">
                  <td style="padding:10px 0;"><strong>${b.brand}</strong></td>
                  <td style="padding:10px 0;">${b.shade}</td>
                  <td style="padding:10px 0;"><span style="display:inline-block; width:16px; height:16px; border-radius:50%; background:${b.tone}; border:1px solid rgba(0,0,0,0.15);"></span></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  $$('.skin-tone-btn').forEach((btn) => {
    btn.addEventListener('click', () => setTone(btn.dataset.tone));
  });

  setTone('neutral');
}

/* ==========================================================================
   SIZE CALCULATOR & SELECTOR (GUIDE.HTML)
   ========================================================================== */
function initSizeCalculator() {
  const form = $('#size-form');
  if (!form) return;

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const h = Number($('#height').value);
    const w = Number($('#weight').value);
    const res = $('#size-result');

    const heightSizes = [[158, 1], [165, 2], [175, 3], [180, 4], [190, 5], [210, 6]];
    const weightSizes = [[55, 1], [65, 2], [75, 3], [90, 4], [110, 5], [135, 6]];
    const hSize = heightSizes.find(([max]) => h <= max)?.[1] || 6;
    const wSize = weightSizes.find(([max]) => w <= max)?.[1] || 6;
    const finalSize = Math.max(hSize, wSize);
    const labels = ['1 · XS', '2 · S', '3 · M', '4 · L', '5 · XL', '6 · XXL / Maxi'];

    res.innerHTML = `
      <div style="background:var(--bg-subtle); padding:16px; border-radius:8px; border:1px solid var(--border);">
        Ориентир вашего размера: <strong style="color:var(--wine); font-size:20px;">${labels[finalSize - 1]}</strong>
        <p style="margin:6px 0 0; font-size:12px; color:var(--ink-muted);">Если ваши рост или вес находятся на границе двух размеров, выбирайте больший для комфорта и долговечности полотна.</p>
      </div>
    `;
  });
}

function initSmartSelector() {
  const form = $('#selector-form');
  if (!form) return;

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const weather = $('#weather').value;
    const occasion = $('#occasion').value;
    const look = $('#look').value;
    const result = $('#selector-result');

    const weatherBase = { warm: 10, mild: 40, cold: 80, frost: 150 }[weather];
    const occasionOffset = { office: 0, evening: -5, active: 10, warmth: 50 }[occasion];
    const lookOffset = { natural: -10, balanced: 0, opaque: 35 }[look];
    const den = Math.max(8, Math.min(300, Math.round((weatherBase + occasionOffset + lookOffset) / 5) * 5));
    const low = Math.max(8, den - 10);
    const high = Math.min(300, den + 10);

    result.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:12px;">
        <span style="font-size:12px; text-transform:uppercase; color:var(--gold); font-weight:700;">Рекомендация алгоритма</span>
        <strong style="font-size:28px; color:#fff; font-family:var(--font-serif);">${low}–${high} DEN</strong>
      </div>
      <p style="font-size:14px; color:#ddd; margin:0 0 12px 0;">
        ${den <= 20 ? 'Рекомендуем ультратонкие модели: Falke Pure Matt 20 или Wolford Individual 20.' : den <= 60 ? 'Оптимальный демисезонный выбор: Omsa Velour 70 или Conte Prestige 40.' : 'Теплый защитный слой: Calzedonia Thermal с кашемиром или Golden Lady Warm & Soft.'}
      </p>
      <a href="brands.html" class="nav-cta-btn" style="display:inline-block; font-size:12px;">Перейти в каталог брендов →</a>
    `;
  });
}

function initCareChecklist() {
  const form = $('#care-form');
  if (!form) return;
  const checks = $$('input[type="checkbox"]', form);
  const text = $('#check-progress-text');
  const bar = $('#check-progress-bar');

  const update = () => {
    const done = checks.filter((c) => c.checked).length;
    if (text) text.textContent = `Готово ${done} из ${checks.length}`;
    if (bar) bar.style.transform = `scaleX(${done / checks.length})`;
  };

  checks.forEach((c) => c.addEventListener('change', update));
  $('#reset-checklist')?.addEventListener('click', () => {
    checks.forEach((c) => (c.checked = false));
    update();
  });
}

// Global Startup
document.addEventListener('DOMContentLoaded', () => {
  initGallery();
  initComparatorButtons();
  initDenSlider();
  initNudeAtlas();
  initSizeCalculator();
  initSmartSelector();
  initCareChecklist();
});

// Immediate execution if script loads late
initGallery();
initComparatorButtons();
initDenSlider();
initNudeAtlas();
initSizeCalculator();
initSmartSelector();
initCareChecklist();
