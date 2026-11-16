/* A small on-site reader. Publisher HTML is never inserted into the page. */
(() => {
  'use strict';
  const date = new Intl.DateTimeFormat('ru-RU', {day:'numeric', month:'long', year:'numeric'});
  const el = (tag, text, cls) => { const n=document.createElement(tag); if(text)n.textContent=text; if(cls)n.className=cls; return n; };
  const dialog = el('dialog', '', 'news-reader');
  dialog.setAttribute('aria-labelledby', 'reader-title');
  const close = el('button', 'Закрыть ×', 'reader-close'); close.type='button'; close.autofocus=true;
  const body=el('div', '', 'reader-body'); dialog.append(close, body); document.body.append(dialog);
  let returnFocus=null, previousOverflow='', openedFromURL=false, closingFromHistory=false;
  function link(label,value,cls){
    try{const u=new URL(value,location.href);if(u.protocol!=='https:'&&u.origin!==location.origin)return null;
      const a=el('a',label,cls);a.href=u.href;if(u.origin!==location.origin){a.target='_blank';a.rel='noopener noreferrer';}return a;
    }catch{return null;}
  }
  function content(item) {
    const sections=Array.isArray(item.sections)?item.sections:[],expanded=sections.length>0;
    const words=[item.summary||item.excerpt||'',...sections.flatMap(s=>s.paragraphs||[])].join(' ').trim().split(/\s+/).length;
    const article=el('article','','reader-article'),head=el('header','','reader-head');
    head.append(el('p',item.ai?'ТОНКО / Новости':expanded?'ТОНКО / Разбор':'ТОНКО / Лента','portal-eyebrow'),el('p',`${item.source} · ${date.format(new Date(item.publishedAt))} · ${expanded?Math.max(2,Math.ceil(words/160))+' мин чтения':'Короткая новость'}${item.ai?' · AI-пересказ':''}`,'news-meta'));
    const heading=el('h2',item.displayTitle||item.title);heading.id='reader-title';heading.lang=item.displayTitle?'ru':item.language;head.append(heading);
    const lead=el('p',item.summary||item.excerpt||'Издание опубликовало материал на эту тему. В его ленте доступен только заголовок; развёрнутый текст для чтения на ТОНКО пока не подготовлен.','reader-excerpt');lead.lang=item.summary?'ru':item.language;head.append(lead);
    const layout=el('div','','reader-layout'),copy=el('div','','reader-copy');
    const photo=item.illustration;
    if(photo&&typeof photo.src==='string'&&(photo.src.startsWith('assets/')||photo.src.startsWith('https://'))){
      const visual=el('figure','','reader-visual'),img=el('img');img.src=photo.src;img.alt=photo.alt||'';img.decoding='async';
      img.addEventListener('error',()=>{visual.remove();layout.classList.remove('has-visual');});
      visual.append(img,el('figcaption',photo.caption||'Иллюстрация к публикации.'));
      const credit=link('Об изображении ↗',photo.source,'reader-image-source');if(credit)visual.append(credit);
      layout.append(visual);layout.classList.add('has-visual');
    }
    sections.forEach(s=>{const section=el('section');if(s.heading)section.append(el('h3',s.heading));(s.paragraphs||[]).forEach(p=>section.append(el('p',p)));copy.append(section);});
    const credits=el('footer','','reader-credits');
    credits.append(el('p',item.ai?'Автоматический пересказ ТОНКО с помощью AI по тексту источника. Может содержать неточности; подробности и актуальные условия — в оригинале.':expanded?'Разбор ТОНКО по указанным источникам. Рекомендации редакции отделены от сообщений изданий.':'Короткий анонс из ленты источника. Полный текст издания здесь не перепечатывается.','reader-credit'));
    const source=link(`Первоисточник: ${item.source} ↗`,item.url,'reader-source');if(source)credits.append(source);
    (item.references||[]).forEach(ref=>{const a=link(ref.label+' ↗',ref.url,'reader-source');if(a)credits.append(a);});
    if(item.via)credits.append(el('p','Ссылка на первоисточник проходит через Google News.','reader-credit'));
    copy.append(credits);layout.append(copy);article.append(head,layout);return article;
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
