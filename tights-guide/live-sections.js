(() => {
  'use strict';
  const seed=document.getElementById('live-seed');if(!seed)return;
  let current,pending;
  const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e;};
  const safeUrl=value=>{try{const u=new URL(value,location.href);return u.protocol==='https:'||(u.origin===location.origin&&u.protocol==='http:');}catch{return false;}};
  const validate=data=>{if(data?.version!==1||!Array.isArray(data.items)||!Array.isArray(data.photos))throw Error('invalid data');data.items=data.items.filter(i=>typeof i.title==='string'&&typeof i.id==='string'&&safeUrl(i.url)&&i.url.startsWith('news.html#story-')&&i.ready&&i.article?.summary&&Array.isArray(i.article.sections)&&i.article.sections.length);return data;};
  try{current=validate(JSON.parse(seed.textContent));}catch{return;}
  const dateFormat=new Intl.DateTimeFormat('ru-RU',{day:'numeric',month:'long',year:'numeric'});
  const checkFormat=new Intl.DateTimeFormat('ru-RU',{day:'numeric',month:'long',hour:'2-digit',minute:'2-digit',timeZone:'Europe/Moscow'});
  const signature=data=>JSON.stringify([data.items,data.photos.map(p=>[p.id,p.contentHash])]);
  const views=[...document.querySelectorAll('[data-live-feed]')].map(section=>({section,filter:'all',limit:6}));
  function status(){
    for(const view of views){
      const e=view.section.querySelector('.live-status'),stamp=Date.parse(current.checkedAt),stale=!Number.isFinite(stamp)||Date.now()-stamp>60*60*1000;
      e.toggleAttribute('data-stale',stale);
      e.textContent=(stale?'Показан сохранённый выпуск. ':'')+(Number.isFinite(stamp)?`Источники проверены ${checkFormat.format(stamp)} МСК. `:'')+'Проверка по расписанию каждые 15 минут; возможны задержки.';
    }
    const e=document.querySelector('.live-photo-status'),stamp=Date.parse(current.photoCheckedAt);
    if(e)e.textContent=(Number.isFinite(stamp)?`Проверено ${checkFormat.format(stamp)} МСК. `:'')+'Новые фотографии проверяются ежедневно.'+(Number.isFinite(stamp)&&Date.now()-stamp>72*60*60*1000?' Обновление задержалось.':'');
  }
  function render(view){
    const {section}=view,list=section.querySelector('.live-list');
    const selected=current.items.filter(i=>(section.dataset.liveFeed!=='men'||i.men)&&(view.filter==='all'||(view.filter==='ru'?i.language==='ru':i.language!=='ru')));
    const fragment=document.createDocumentFragment();
    for(const item of selected.slice(0,view.limit)){
      const article=node('article',null,'live-item');article.dataset.liveItem=item.id;
      if(item.image&&/^assets\/[a-zA-Z0-9/_\-.]+$/.test(item.image.src)){
        const image=node('img');image.src=item.image.src;image.alt=item.image.alt||item.title;image.width=item.image.width;image.height=item.image.height;image.loading='lazy';image.decoding='async';if(item.image.srcset)image.srcset=item.image.srcset;image.sizes='(max-width:700px) 90vw, 40vw';article.append(image);
      }
      const meta=node('div',null,'live-meta');meta.append(node('span',item.source));
      const stamp=Date.parse(item.publishedAt);
      if(window.TonkoPublication)meta.append(window.TonkoPublication.create(item.publishedAt));
      else if(Number.isFinite(stamp)){const t=node('time','Опубликовано '+dateFormat.format(stamp));t.dateTime=item.publishedAt;meta.append(t);}else meta.append(node('span','Дата публикации не указана'));
      const heading=node('h3'),title=node('a',item.title),link=node('a',item.ready?'Читать на ТОНКО →':item.via?'Открыть через Google News ↗':'Полный текст у источника ↗','live-link');
      for(const a of [title,link]){a.href=item.url;if(!item.ready){a.target='_blank';a.rel='noopener noreferrer';}}
      for(const a of [title,link])a.addEventListener('click',event=>{if(window.TonkoReader&&!event.ctrlKey&&!event.metaKey&&!event.shiftKey){event.preventDefault();window.TonkoReader.open(item.article);}});
      heading.append(title);article.append(meta,heading);
      if(item.excerpt){const p=node('p',item.excerpt);p.lang=item.ready?'ru':item.language||'en';article.append(p);}
      article.append(link);fragment.append(article);
    }
    if(!selected.length)fragment.append(node('p','В этой подборке пока нет публикаций. Выберите «Все материалы».'));
    list.replaceChildren(fragment);section.querySelector('.live-more').hidden=view.limit>=selected.length;
    section.querySelectorAll('[data-live-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.liveFilter===view.filter)));
  }
  for(const view of views){
    view.section.querySelector('.live-filters').hidden=false;
    view.section.querySelectorAll('[data-live-filter]').forEach(b=>b.addEventListener('click',()=>{view.filter=b.dataset.liveFilter;view.limit=6;render(view);}));
    view.section.querySelector('.live-more').addEventListener('click',()=>{const previous=view.limit;view.limit+=6;render(view);if(view.section.querySelector('.live-more').hidden)view.section.querySelectorAll('.live-item h3 a')[previous]?.focus({preventScroll:true});});
    view.section.querySelector('.live-refresh').addEventListener('click',()=>{if(!pending)return;current=pending;pending=null;views.forEach(v=>{v.limit=6;render(v);v.section.querySelector('.live-refresh').hidden=true;});status();view.section.querySelector('[data-live-filter]').focus({preventScroll:true});});
    render(view);
  }
  status();
  const openFromUrl=()=>{const id=new URLSearchParams(location.search).get('news');const item=current.items.find(i=>i.id===id);if(item&&window.TonkoReader)window.TonkoReader.open(item.article,true);else if(!id)window.TonkoReader?.close();};
  openFromUrl();addEventListener('popstate',openFromUrl);
  async function check(){
    if(document.hidden)return;
    try{
      const response=await fetch('data/live-feed.json?t='+Math.floor(Date.now()/60000),{cache:'no-store',signal:AbortSignal.timeout(15000)});
      if(!response.ok)throw Error('network');const next=validate(await response.json());
      if(signature(next)!==signature(current)){pending=next;current.checkedAt=next.checkedAt;current.photoCheckedAt=next.photoCheckedAt;status();views.forEach(v=>v.section.querySelector('.live-refresh').hidden=false);}
      else {current=next;status();}
    }catch{ /* Keep the last readable edition; its date exposes a delayed refresh. */ }
  }
  check();setInterval(check,60000);addEventListener('visibilitychange',()=>{if(!document.hidden){status();check();}});
})();
