/* A small on-site reader. Publisher HTML is never inserted into the page. */
(() => {
  'use strict';
  const date = new Intl.DateTimeFormat('ru-RU', {day:'numeric', month:'long', year:'numeric'});
  const el = (tag, text, cls) => { const n=document.createElement(tag); if(text)n.textContent=text; if(cls)n.className=cls; return n; };
  const dialog = el('dialog', '', 'news-reader');
  dialog.setAttribute('aria-label', 'Читать новость на ТОНКО');
  const close = el('button', 'Закрыть ×', 'reader-close'); close.type='button'; close.autofocus=true;
  const body=el('div', '', 'reader-body'); dialog.append(close, body); document.body.append(dialog);
  let returnFocus=null, previousOverflow='', openedFromURL=false, closingFromHistory=false;
  const contexts=[
    {pattern:/упаков|packag/i, image:'ss-pack', label:'Детали бренда', text:'На упаковке полезно сверить состав, размерную сетку, плотность и обозначения ухода. Одинаковое число DEN у разных моделей не гарантирует одинаковые прозрачность и посадку.', link:'lookbook.html?filter=packaging', action:'Рассмотреть упаковки'},
    {pattern:/тёпл|тепл|winter|wool|шерст|warm/i, image:'outfit-soft-knit', label:'Сезон и фактура', text:'В зимнем образе обращайте внимание на состав и фактуру: плотность DEN сама по себе не описывает тепло. Сравните материал колготок с обувью и верхним слоем одежды.', link:'guide.html', action:'Открыть мастерскую выбора'},
    {pattern:/lace|круж|dots|горох|pattern|фактур|рисун|argyle/i, image:'ss-lace', label:'Рисунок в образе', text:'Чтобы рассмотреть рисунок, начните с простого однотонного верха. Повтор цвета в обуви или аксессуарах помогает связать детали образа.', link:'lookbook.html?filter=pattern', action:'Посмотреть рисунки'},
    {pattern:/.*/, image:'ss-clara', label:'Колготки в гардеробе', text:'Попробуйте собрать сочетание вокруг одной детали: оттенка, прозрачности или фактуры. В галерее можно сравнить готовые образы и сохранить понравившиеся фотографии.', link:'lookbook.html?filter=outfits', action:'Посмотреть образы'}
  ];
  function content(item) {
    const c=contexts.find(c=>c.pattern.test(item.title));
    const wrap=el('div','','reader-layout'),visual=el('figure','','reader-visual');
    const img=el('img');img.src=`assets/editorial/${c.image}.${c.image==='outfit-soft-knit'?'webp':'jpg'}`;img.alt=c.label;img.loading='lazy';
    visual.append(img,el('figcaption',(c.image.startsWith('ss-')?'Swedish Stockings. ':'Подборка владельца ТОНКО. ')+'Иллюстрация из галереи, не фотография события.'));
    const copy=el('div','','reader-copy');
    copy.append(el('p','ТОНКО / В фокусе','portal-eyebrow'),el('p',`${item.source} · ${date.format(new Date(item.publishedAt))}`,'news-meta'));
    const heading=el('h2',item.displayTitle||item.title); heading.lang=item.displayTitle?'ru':item.language==='ru'?'ru':'en'; copy.append(heading);
    copy.append(el('p',item.summary?'Кратко по материалу':'Анонс источника','reader-label'));
    const brief=el('p',item.summary || item.excerpt || 'Источник опубликовал материал на эту тему. В ленте доступен только заголовок; развёрнутый анонс редакция пока не предоставила.','reader-excerpt');
    brief.lang=item.summary?'ru':item.language==='ru'?'ru':'en';copy.append(brief);
    if(item.excerpt||item.summary)copy.append(el('p',item.summary?'Краткий пересказ ТОНКО по публикации источника.':'Короткий анонс из ленты источника. Полный текст принадлежит издателю.','reader-credit'));
    const note=el('aside','','reader-note');note.append(el('h3',c.label),el('p',c.text),el('p','Заметка ТОНКО · совет по теме, не пересказ публикации','reader-credit'));
    const related=el('a',c.action+' →');related.href=c.link;note.append(related);copy.append(note);
    const source=el('a',`Первоисточник: ${item.source} ↗`,'reader-source');
    try{const url=new URL(item.url);if(url.protocol==='https:'){source.href=url.href;source.target='_blank';source.rel='noopener noreferrer';copy.append(source);}}catch{}
    if(item.via)copy.append(el('p','Ссылка на первоисточник проходит через Google News.','reader-credit'));
    wrap.append(visual,copy); return wrap;
  }
  function dismiss(){if(dialog.open)dialog.close();}
  dialog.addEventListener('close',()=>{
    document.documentElement.style.overflow=previousOverflow;
    if(!closingFromHistory){const url=new URL(location.href); url.searchParams.delete('news');history.replaceState(null,'',url);}
    closingFromHistory=false;
    returnFocus?.focus({preventScroll:true}); openedFromURL=false;
  });
  close.addEventListener('click',dismiss);
  dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dismiss();}});
  window.TonkoReader={close(){if(dialog.open){closingFromHistory=true;dialog.close();}},open(item, fromURL=false){
    if(!item)return;
    if(!dialog.open){returnFocus=document.activeElement;previousOverflow=document.documentElement.style.overflow;dialog.showModal();}
    body.replaceChildren(content(item));dialog.scrollTop=0;document.documentElement.style.overflow='hidden';close.focus();
    const url=new URL(location.href);url.searchParams.set('news',item.id);
    if(!fromURL&&!openedFromURL)history.pushState(null,'',url);else history.replaceState(null,'',url);
    openedFromURL=true;
  }};
})();
