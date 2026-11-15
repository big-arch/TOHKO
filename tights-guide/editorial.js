(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  const esc = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money = n => new Intl.NumberFormat('ru-RU',{style:'currency',currency:'RUB',maximumFractionDigits:2}).format(n);
  const press = (buttons,selected) => buttons.forEach(b=>b.setAttribute('aria-pressed',String(b===selected)));

  async function gallery() {
    const grid=$('#editorial-gallery'); if(!grid)return;
    const dialog=$('#editorial-lightbox'), full=$('#editorial-full-image');
    let media=[],shown=[],current=0,opener=null,activeFilter='all';
    let saved=new Set();
    try{const raw=JSON.parse(localStorage.getItem('tonko-photo-shelf-v1')||'[]');if(Array.isArray(raw))saved=new Set(raw.filter(x=>typeof x==='string'));}catch{}
    const status=document.createElement('p');status.className='photo-save-status';status.setAttribute('role','status');$('.gallery-toolbar').append(status);
    const detailIds=new Set(['wolford-3','noq-lace','calzedonia-glitter','cdr-gloss','gabriella-arctic']);
    const savePhoto=id=>{
      const next=new Set(saved);next.has(id)?next.delete(id):next.add(id);
      try{localStorage.setItem('tonko-photo-shelf-v1',JSON.stringify([...next]));saved=next;status.textContent=next.has(id)?'Фотография сохранена в этом браузере.':'Фотография удалена из вашей подборки.';return true;}
      catch{status.textContent='Браузер запретил сохранение. Фотографии по-прежнему можно смотреть.';const note=$('#editorial-photo-credit');if(dialog.open)note.textContent='Браузер запретил сохранение. Закройте просмотр, чтобы продолжить.';return false;}
    };
    try {
      const response=await fetch('data/editorial-media.json', {cache:'no-cache'});
      if(!response.ok)throw new Error('media');
      media=(await response.json()).filter(p=>!['business','archive'].includes(p.category));
      saved=new Set([...saved].filter(id=>media.some(p=>p.id===id)));
    } catch {
      grid.innerHTML='<p>Не удалось загрузить подборку. <button type="button" id="retry-gallery">Попробовать ещё раз</button></p>';
      $('#retry-gallery').onclick=gallery;return;
    }
    const update=()=>{
      const p=shown[current];if(!p)return;
      full.src=p.image;full.alt=p.alt;
      // Small supplied images retain their natural size in the enlarged viewer.
      full.style.maxWidth=`min(100%, ${p.width}px)`;
      $('#editorial-photo-title').textContent=p.title;
      $('#editorial-photo-caption').textContent=p.caption;
      $('#editorial-photo-credit').textContent=p.origin==='user'?'Присланный пример · '+p.width+' × '+p.height+' px. Автор и исходная публикация пока не установлены.':p.author+' · '+p.license;
      $('#editorial-photo-number').textContent=`${current+1} / ${shown.length}`;
      const source=$('#editorial-photo-source');source.href=p.origin==='user'?'sources.html#photography':p.source;
      source.textContent=p.origin==='user'?'О происхождении подборки ↗':'Открыть источник ↗';
      let save=$('#lightbox-save');
      if(!save){save=document.createElement('button');save.type='button';save.id='lightbox-save';save.className='gallery-save';$('.lightbox-info').append(save);save.addEventListener('click',()=>{const id=shown[current]?.id;if(!id||!savePhoto(id))return;if(activeFilter==='saved'){dialog.close();render(activeFilter);}else{render(activeFilter);update();}});}
      save.textContent=saved.has(p.id)?'Сохранено ✓':'Сохранить фотографию';save.setAttribute('aria-pressed',String(saved.has(p.id)));
      let detail=$('#lightbox-detail');if(!detail){detail=document.createElement('a');detail.id='lightbox-detail';detail.className='photo-detail-link';detail.textContent='Рассмотреть под лупой ↗';$('.lightbox-info').append(detail);}detail.hidden=!detailIds.has(p.id);detail.href='textures.html?photo='+encodeURIComponent(p.id);
    };
    const change=(step)=>{current=(current+step+shown.length)%shown.length;update();};
    const render=filter=>{
      activeFilter=filter;shown=filter==='all'?media:media.filter(p=>filter==='saved'?saved.has(p.id):p.category===filter);
      grid.innerHTML=shown.map((p,i)=>`<article class="gallery-item" id="photo-${esc(p.id)}"><button class="gallery-open" type="button" data-photo-index="${i}" aria-label="Открыть: ${esc(p.title)}"><img src="${esc(p.image)}" alt="${esc(p.alt)}" width="${p.width}" height="${p.height}" loading="${i<2?'eager':'lazy'}" decoding="async" ${i===0?'fetchpriority="high"':''} ${p.srcset?`srcset="${esc(p.srcset)}" sizes="${grid.classList.contains('gallery-large')?'(max-width:540px) 100vw, 50vw':'(max-width:540px) 50vw, (max-width:1100px) 33vw, 25vw'}"`:''} class="${['packaging','texture'].includes(p.category)||p.id==='wolford-4'?'contain':''}"></button><h2>${esc(p.title)}</h2><p>${esc(p.origin==='user'?'Пример из подборки':p.author)}</p><button type="button" class="gallery-save" data-save-photo="${esc(p.id)}" aria-label="${saved.has(p.id)?'Убрать из подборки':'Сохранить фотографию'}: ${esc(p.title)}" aria-pressed="${saved.has(p.id)}">${saved.has(p.id)?'Сохранено ✓':'Сохранить'}</button></article>`).join('');
      $('#gallery-count').textContent=`Фотографий: ${shown.length}`;$('#gallery-empty').hidden=shown.length>0;
      const savedCount=$('#photo-saved-count');if(savedCount)savedCount.textContent=saved.size;
      $('#gallery-empty').textContent=filter==='saved'?'В вашей подборке пока нет фотографий. Откройте коллекцию и нажмите «Сохранить» под понравившимся кадром.':'В этой подборке пока нет фотографий.';
      grid.querySelectorAll('[data-save-photo]').forEach(b=>b.addEventListener('click',()=>{const id=b.dataset.savePhoto;if(savePhoto(id)){render(activeFilter);(grid.querySelector(`[data-save-photo="${CSS.escape(id)}"]`)||$('[data-gallery-filter="saved"]'))?.focus({preventScroll:true});}}));
      grid.querySelectorAll('[data-photo-index]').forEach(b=>b.addEventListener('click',()=>{
        current=Number(b.dataset.photoIndex);opener=b;update();dialog.showModal();document.body.classList.add('editorial-modal-open');
      }));
    };
    const filters=$$('[data-gallery-filter]');
    const initial=new URLSearchParams(location.search).get('filter');
    let selected=filters.find(b=>b.dataset.galleryFilter===initial)||filters[0];
    press(filters,selected);render(selected.dataset.galleryFilter);
    $$('[data-feature-photo]').forEach(link=>link.addEventListener('click',event=>{
      const id=link.dataset.featurePhoto;
      if(!media.some(p=>p.id===id))return;
      event.preventDefault();
      if(!shown.some(p=>p.id===id)){
        const all=filters.find(b=>b.dataset.galleryFilter==='all');press(filters,all);render('all');
        const url=new URL(location.href);url.searchParams.delete('filter');history.replaceState(null,'',url);
      }
      current=shown.findIndex(p=>p.id===id);opener=link;update();dialog.showModal();document.body.classList.add('editorial-modal-open');
    }));
    const linked=media.find(p=>location.hash===`#photo-${p.id}`);
    if(linked){const index=shown.findIndex(p=>p.id===linked.id);if(index>=0)grid.querySelector(`[data-photo-index="${index}"]`)?.click();}
    filters.forEach(b=>b.addEventListener('click',()=>{press(filters,b);render(b.dataset.galleryFilter);const url=new URL(location.href);b.dataset.galleryFilter==='all'?url.searchParams.delete('filter'):url.searchParams.set('filter',b.dataset.galleryFilter);history.replaceState(null,'',url);}));
    $('[data-photo-prev]').onclick=()=>change(-1);$('[data-photo-next]').onclick=()=>change(1);
    $('.lightbox-close').onclick=()=>dialog.close();
    dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
    dialog.addEventListener('close',()=>{document.body.classList.remove('editorial-modal-open');(opener?.isConnected?opener:document.querySelector(`[data-gallery-filter="${CSS.escape(activeFilter)}"]`))?.focus({preventScroll:true});});
    dialog.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'){e.preventDefault();change(-1);}if(e.key==='ArrowRight'){e.preventDefault();change(1);}});
  }
  gallery();

  const picker=$('#pair-picker');
  if(picker){
    const update=()=>{
      const d=new FormData(picker),occasion=d.get('occasion'),look=d.get('look');
      const context={daily:'На каждый день: начните с посадки и совместимости с обувью.',evening:'Для выразительного образа: решите, где будет акцент — на блеске, рисунке или прозрачности.',under:'Под брюки: важны гладкая поверхность, комфортный пояс и подходящая температура.',sport:'Для тренировки: начните со спортивных легинсов или тайтсов, рассчитанных на движения.'};
      const visual={sheer:'Смотрите тонкие прозрачные модели, часто в диапазоне 10–30 DEN. Проверяйте вид на ноге: одно число не гарантирует прозрачность.',opaque:'Ищите плотный матовый трикотаж. 60–120 DEN часто служит отправной точкой, но проверка непрозрачности важнее числа.',pattern:'Сравните масштаб рисунка и швы. Сетка и сложные узоры не описываются одним значением DEN.'};
      const priority={waist:'Пояс: присядьте и наклонитесь. Он должен удерживать вещь без постоянного поправления и болезненного давления.',seams:'Швы: проверьте центральный шов, ластовицу и мысок под той одеждой и обувью, с которой будете носить пару.',wear:'Износ: посмотрите на усиление мыска и рекомендации по уходу. Обещание «не рвутся» требует условий испытания, а не только рекламы.'};
      $('#pair-result').innerHTML=`<h3>${context[occasion]}</h3><p>${occasion==='sport'?'Для активных движений проверьте непрозрачность при приседании, отвод влаги и устойчивость пояса. Прозрачный или сетчатый эффект лучше оценивать как вставку либо отдельный слой, а не доказательство спортивных свойств.':visual[look]}</p><p>${priority[d.get('priority')]}</p><p><a href="${occasion==='sport'?'leggings.html':'atlas.html'}">${occasion==='sport'?'Подробнее о легинсах':'Перейти к проверке посадки'} →</a></p>`;
    };picker.addEventListener('change',update);picker.addEventListener('submit',e=>e.preventDefault());update();
  }
  const den=$('#lab-den');
  if(den){
    const stretch=$('#lab-stretch'),tone=$('#lab-tone');
    const update=()=>{
      const d=Number(den.value),s=Number(stretch.value)/100;
      $('#lab-den-number').textContent=d+' DEN';$('#lab-stretch-number').textContent=s.toLocaleString('ru-RU')+'×';
      $('#lab-current-label').textContent=`${d} DEN · растяжение ${s.toLocaleString('ru-RU')}×`;
      $$('.fabric-swatch').forEach(el=>el.style.setProperty('--skin',{light:'#e2c9ad',medium:'#b98b67',deep:'#76513e'}[tone.value]));
      const swatch=$('.fabric-swatch.variable');swatch.style.setProperty('--fabric-opacity',String(Math.min(.93,(.12+d*.0098)/s)));swatch.style.setProperty('--mesh-size',3*s+'px');
      $('#lab-den-text').textContent=d<=20?'Тонкая нить: обычно выбирают для лёгкого прозрачного эффекта. Растяжение меняет распределение петель и вид полотна.':d<=40?'Средний диапазон: прозрачность может заметно различаться между моделями. Сравнивайте реальные фотографии и состав.':'Более высокая линейная плотность нити. Она сама по себе не доказывает непрозрачность, тепло или медицинскую компрессию.';
      $$('[data-den]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.den)===d)));
    };
    [den,stretch,tone].forEach(e=>e.addEventListener('input',update));
    $$('[data-den]').forEach(b=>b.onclick=()=>{den.value=b.dataset.den;update();});update();
  }
  const parts={
    waist:['Пояс','Удерживает изделие на талии. Широкий не обязательно мягче: имеют значение натяжение, эластичность и форма тела. Присядьте, наклонитесь и проверьте, не сворачивается ли край.'],
    seam:['Швы','Соединяют участки изделия и могут ощущаться под облегающей одеждой. Проверьте расположение и плоскость шва. Формулировка «бесшовные» требует уточнения: какая именно зона не имеет шва?'],
    gusset:['Ластовица','Вставка в шаговой зоне, которая меняет конструкцию и распределение натяжения. Материал и наличие вставки различаются по моделям. Она должна находиться на месте, без провисания и чрезмерного давления.'],
    toe:['Мысок','Усиленный мысок может быть заметен в открытой обуви. Гладкий прозрачный выглядит иначе, но не гарантирует стойкость. Проверьте длину стопы, шов и состояние ногтей.'],
    leg:['Длина и натяжение','Если длины не хватает, натяжение распределяется неравномерно, верх сползает и полотно меняет прозрачность. Сверяйте рост, обхваты и таблицу именно этой модели. Больший размер не всегда решает проблему кроя.']
  };
  const partButtons=$$('[data-part]');
  if(partButtons.length){const select=b=>{press(partButtons,b);const p=parts[b.dataset.part];$('#part-detail').innerHTML=`<h3>${p[0]}</h3><p>${p[1]}</p>`;};partButtons.forEach(b=>b.onclick=()=>select(b));select(partButtons[0]);}

  const quiz=$('#fabric-quiz');
  if(quiz){
    const questions=[
      ['Что означает 20 DEN?',['Массу 9000 метров нити: 20 граммов','Толщину полотна 20 микрон','20% эластана'],0,'DEN — единица линейной плотности нити. Это не процент состава и не толщина готовой ткани.'],
      ['Две модели 40 DEN обязательно одинаково прозрачные?',['Да, число определяет всё','Нет, важны вязка, цвет и растяжение'],1,'Одинаковая линейная плотность не делает одинаковыми структуру полотна, цвет, посадку и освещение.'],
      ['Высокий DEN доказывает медицинскую компрессию?',['Да, чем выше — тем лечебнее','Нет, это разные характеристики'],1,'Медицинская компрессия характеризуется давлением и назначением. Её не подбирают по DEN.'],
      ['Как проверить легинсы для приседаний?',['Только посмотреть состав','Присесть в своём размере при хорошем освещении','Всегда купить на размер меньше'],1,'Важен вид ткани под натяжением, устойчивость пояса и свобода движения. Состав — лишь часть информации.'],
      ['Для размера достаточно универсального совета «берите больше»?',['Нет, нужна таблица модели и примерка','Да, размер всегда решает всё'],0,'Рост, обхваты, длина и крой взаимодействуют. Слишком большой размер тоже может давать складки и сползать.']
    ];
    let index=0,score=0,answered=false;
    const next=$('#quiz-next');
    const render=()=>{
      answered=false;next.hidden=true;$('#quiz-feedback').textContent='';$('#quiz-progress').value=index;
      if(index===questions.length){$('#quiz-position').textContent='Готово';$('#quiz-question').textContent=`Верных ответов: ${score} из ${questions.length}`;$('#quiz-options').replaceChildren();$('#quiz-feedback').textContent='Теперь у вас есть опорные критерии. При выборе конкретной пары всё равно проверьте размер, состав и посадку.';next.textContent='Пройти ещё раз';next.hidden=false;return;}
      const q=questions[index];$('#quiz-position').textContent=`Вопрос ${index+1} / ${questions.length}`;$('#quiz-question').textContent=q[0];
      $('#quiz-options').innerHTML=q[1].map((t,i)=>`<button type="button" data-answer="${i}">${t}</button>`).join('');
      $$('#quiz-options button').forEach(b=>b.onclick=()=>{
        if(answered)return;answered=true;const correct=Number(b.dataset.answer)===q[2];if(correct)score++;
        $$('#quiz-options button').forEach(x=>{x.disabled=true;if(Number(x.dataset.answer)===q[2])x.classList.add('correct');});if(!correct)b.classList.add('incorrect');
        $('#quiz-feedback').textContent=(correct?'Верно. ':'Правильный ответ выделен. ')+q[3];$('#quiz-progress').value=index+1;next.textContent=index===4?'Посмотреть результат':'Следующий вопрос';next.hidden=false;next.focus({preventScroll:true});
      });
    };next.onclick=()=>{if(index===questions.length){index=0;score=0;}else index++;render();const target=$('#quiz-options button')||next;target.focus({preventScroll:true});};render();
  }
  const care=$('#care-checklist');
  if(care){const update=()=>$('#care-check-count').textContent=`Проверено: ${care.querySelectorAll('input:checked').length} из ${care.querySelectorAll('input').length}`;care.addEventListener('change',update);care.addEventListener('reset',()=>{$('#care-check-count').textContent=`Проверено: ${[...care.querySelectorAll('input')].filter(i=>i.defaultChecked).length} из ${care.querySelectorAll('input').length}`;});care.addEventListener('submit',e=>e.preventDefault());update();}
  const cost=$('#cost-wear');
  if(cost){const update=()=>{const p=cost.elements.price,w=cost.elements.wears;$('#cost-wear-result').textContent=p.value!==''&&w.value!==''&&p.validity.valid&&w.validity.valid?money(Number(p.value)/Number(w.value))+' за одну носку':'Укажите цену от 0 и число носок от 1.';};cost.addEventListener('input',update);cost.addEventListener('submit',e=>e.preventDefault());update();}

  const scenarios={
    leggings:{yoga:['Йога и растяжка','Проверьте свободу в глубоких наклонах, мягкость пояса и швы в зонах контакта с ковриком. Приседание помогает заметить просвечивание; большой процент эластана сам по себе не гарантирует удобство.'],run:['Бег','Пояс должен держаться в движении, карманы — удерживать вещи без раскачивания. Учитывайте погоду, длину, отвод влаги и видимость в темноте. Плотность и тепло оценивают по всей конструкции.'],gym:['Силовая тренировка','Проверьте приседание и выпад: не просвечивает ли ткань, не сползает ли пояс, не ограничивает ли шаговый шов. Соприкосновение с грубыми поверхностями ускоряет износ.'],city:['Город','Сравните трикотаж с более формованными моделями: матовость, карманы, длина и способность сохранять форму важнее спортивного названия. Проверяйте вид при дневном свете.']},
    men:{under:['Незаметный слой','Начните с гладкой модели подходящей длины. Примерьте под обычными брюками, сядьте и пройдитесь. Пояс и мысок не должны давить; наличие гульфика и форма верхней части зависят от модели.'],shorts:['С шортами','Сопоставьте длину шорт, плотность слоя и обувь. Матовый чёрный создаёт спокойную основу, прозрачный сильнее меняет визуальный образ. Это вопрос стиля, а не отдельная медицинская функция.'],statement:['Выразительный образ','Рисунок, блеск и контрастный цвет могут стать главным акцентом. Сначала выберите одну ведущую фактуру, затем оцените пропорции в полный рост. Повторите один из цветов рисунка в пиджаке, рубашке или обуви.'],stage:['Сцена и движение','Для танца или сцены выбирайте изделие по требованиям движения и костюма. Важны длина, растяжимость, швы и совместимость с обувью. Обычная тонкая пара не автоматически заменяет специализированные танцевальные тайтсы.']},
    business:{yarn:['01 / Нить','Сырьё задаёт часть свойств, стоимости и доступности производства. Закупщик проверяет состав, стабильность поставок и спецификацию. Маркетинговое имя волокна не заменяет технических требований.'],knit:['02 / Вязание','Оборудование, программа вязания и контроль натяжения формируют петли и зоны изделия. Здесь важны повторяемость размеров, дефекты полотна, загрузка машин и квалификация персонала.'],finish:['03 / Отделка и контроль','Окрашивание, формование, соединение деталей и проверка влияют на итоговую посадку и внешний вид. Контроль партии должен учитывать оттенок, размер, швы и дефекты. Схема операций зависит от технологии.'],retail:['04 / Продажа','В цену входят не только материал и работа: есть упаковка, доставка, комиссия канала, фотосъёмка, поддержка, продвижение и возвраты. Онлайн-продажа не означает отсутствие торговых расходов.'],repeat:['05 / Повторная покупка','Вторая покупка зависит от соответствия ожиданиям: посадки, срока носки, наличия нужной модели и сервиса. Полезно разбирать причины возвратов по размерам, а не только считать общий оборот.']}
  };
  $$('.scenario-selector').forEach(root=>{const options=scenarios[root.dataset.scenarios];if(!options)return;const bs=[...root.querySelectorAll('[data-scenario]')],result=root.querySelector('.scenario-result');const select=b=>{press(bs,b);const [h,p]=options[b.dataset.scenario];result.innerHTML=`<h3>${h}</h3><p>${p}</p>`;};bs.forEach(b=>b.onclick=()=>select(b));select(bs[0]);});
  const unit=$('#unit-form');
  if(unit){const update=()=>{const inputs=[...unit.querySelectorAll('input')],out=$('#unit-result');if(inputs.some(x=>x.value===''||!x.validity.valid)){out.textContent='Заполните все поля неотрицательными числами. Комиссия — от 0 до 100%.';out.classList.remove('loss');return;}const v=Object.fromEntries(inputs.map(i=>[i.name,Number(i.value)]));const commission=v.price*v.fee/100,contribution=v.price-v.cost-commission-v.shipping-v.ads-v.returns;out.classList.toggle('loss',contribution<0);out.innerHTML=`<h3>Вклад на покрытие с одной пары</h3><strong>${money(contribution)}</strong><p>Комиссия канала: ${money(commission)}.${v.price>0?' Доля вклада в цене: '+(contribution/v.price*100).toLocaleString('ru-RU',{maximumFractionDigits:1})+'%.':''}</p><p>${contribution<0?'При этих вводных переменные расходы уже выше цены продажи.':contribution===0?'Цена ровно покрывает введённые переменные расходы.':'Этой суммой ещё нужно покрыть постоянные расходы и другие неучтённые затраты.'}</p>`;};unit.addEventListener('input',update);unit.addEventListener('submit',e=>e.preventDefault());update();}
})();
