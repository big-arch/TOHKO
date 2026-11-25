(() => {
  'use strict';
  const list=document.getElementById('news-list'); if(!list)return;
  const status=document.getElementById('news-status'), refresh=document.getElementById('news-refresh');
  const fresh=document.getElementById('news-new'), more=document.getElementById('news-more');
  const filters=[...document.querySelectorAll('[data-news-language]')];
  const publication=window.TonkoPublication;
  const checkedFormat=new Intl.DateTimeFormat('ru-RU',{day:'numeric',month:'long',hour:'2-digit',minute:'2-digit'});
  let current=null,pending=null,language='all',limit=6,busy=false;
  try{current=validate(JSON.parse(document.getElementById('news-seed').textContent));}catch{}
  const node=(tag,text,cls)=>{const el=document.createElement(tag);if(text)el.textContent=text;if(cls)el.className=cls;return el;};
  const signature=data=>JSON.stringify(data.items.map(i=>[i.id,i.title,i.displayTitle,i.excerpt,i.summary,i.sections,i.illustration,i.references,i.ai,i.publishedAt]));
  function ready(i){
    if(typeof i.summary!=='string'||i.summary.length<30||!Array.isArray(i.sections)||!i.sections.length)return false;
    if(!i.sections.every(s=>s&&typeof s.heading==='string'&&Array.isArray(s.paragraphs)&&s.paragraphs.length&&s.paragraphs.every(p=>typeof p==='string'&&p.length>=30)))return false;
    return ([i.summary,...i.sections.flatMap(s=>s.paragraphs)].join(' ').match(/[\p{L}\p{N}_]+/gu)||[]).length>=65;
  }
  function validate(data){
    if(data.version!==1||!Array.isArray(data.items)||!Array.isArray(data.sources))throw Error('Invalid news data');
    const all=data.items.filter(i=>{
      try{return typeof i.title==='string'&&i.title.length>0&&new URL(i.url).protocol==='https:';}catch{return false;}
    });
    data.backlog=all.filter(i=>!ready(i));data.items=all.filter(ready).sort((a,b)=>publication.compareNewest(a.publishedAt,b.publishedAt));
    return data;
  }
  function updateStatus(data){
    const stamp=Date.parse(data.lastSuccessfulAt),age=Date.now()-stamp;
    const failed=data.sources.filter(s=>s.status!=='ok').length;
    const stale=!Number.isFinite(stamp)||age>60*60*1000;
    status.dataset.state=stale?'stale':'ok';
    status.textContent=!Number.isFinite(stamp)?'Успешная проверка источников пока не выполнена.':
      `${stale?'Показан сохранённый выпуск. ':''}Проверено ${checkedFormat.format(new Date(stamp))}. `+
      (failed?`Недоступно источников: ${failed} из ${data.sources.length}. `:'')+'Проверка по расписанию каждые 15 минут.';
    const queue=document.getElementById('news-queue');
    if(queue){
      const backlog=data.backlog||[];
      queue.replaceChildren(node('p',`Полных статей: ${data.items.length}. Обнаружено без пересказа: ${backlog.length}. Тематические анонсы доступны в подборке источников; новые AI-пересказы отключены.`));
    }
    const sources=document.getElementById('news-sources');sources.replaceChildren();
    data.sources.forEach(s=>{
      const li=node('li'),a=node('a',s.name);
      try{if(new URL(s.site).protocol!=='https:')return;}catch{return;}
      a.href=s.site;a.target='_blank';a.rel='noopener noreferrer';
      li.append(a,node('span',s.status==='ok'?'Доступен':'Временно недоступен'));sources.append(li);
    });
  }
  function render(){
    if(!current)return;
    const items=current.items.filter(i=>language==='all'||i.language===language);
    const fragment=document.createDocumentFragment();
    items.slice(0,limit).forEach(i=>{
      const article=node('article',null,'news-item'),meta=node('div',null,'news-meta');
      article.dataset.publishedAt=i.publishedAt||'';
      meta.append(node('span',i.source+(i.via?' · через Google News':'')),publication.create(i.publishedAt),node('span',i.language==='ru'?'RU':'EN'));
      const title=node('h3'),link=node('a',i.displayTitle||i.title);
      link.href=`news.html#story-${i.id}`;link.dataset.newsId=i.id;link.lang=i.displayTitle?'ru':i.language==='ru'?'ru':'en';
      title.append(link);article.append(meta,title,node('span',i.ai?'AI-пересказ · Читать →':'Разбор ТОНКО · Читать →','news-read'));fragment.append(article);
    });
    if(!items.length)fragment.append(node('p','Пока нет публикаций на выбранном языке. Посмотрите общую ленту.'));
    list.replaceChildren(fragment);more.hidden=items.length<=limit;
    more.textContent=`Ещё публикации (${Math.max(0,items.length-limit)}) ↓`;
  }
  async function check(manual=false){
    if(busy||(!manual&&document.hidden))return;
    busy=true;refresh.disabled=true;
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
    try{
      const response=await fetch(`data/news.json?t=${Math.floor(Date.now()/60000)}`,{cache:'no-store',signal:controller.signal});
      if(!response.ok)throw Error('Network');
      const data=validate(await response.json());updateStatus(data);
      if(!current){current=data;render();}
      else if(signature(current)!==signature(data)){
        pending=data;fresh.hidden=false;
        const known=new Set(current.items.map(i=>i.id));const count=data.items.filter(i=>!known.has(i.id)).length;
        fresh.textContent=count?`Новых публикаций: ${count}. Показать ↑`:'Лента обновилась. Показать изменения ↑';
      }else{current=data;pending=null;fresh.hidden=true;}
    }catch{
      status.dataset.state='stale';status.textContent='Не удалось проверить обновления. Показан сохранённый выпуск; попробуйте позже.';
    }finally{clearTimeout(timeout);busy=false;refresh.disabled=false;}
  }
  filters.forEach(button=>button.addEventListener('click',()=>{
    language=button.dataset.newsLanguage;limit=6;
    filters.forEach(b=>b.setAttribute('aria-pressed',String(b===button)));render();
  }));
  more.addEventListener('click',()=>{limit+=6;render();});
  fresh.addEventListener('click',()=>{if(pending){current=pending;pending=null;limit=6;render();fresh.hidden=true;refresh.focus({preventScroll:true});}});
  refresh.addEventListener('click',()=>check(true));
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)check();});
  list.addEventListener('click',event=>{
    const link=event.target.closest('[data-news-id]');if(!link||!window.TonkoReader||event.ctrlKey||event.metaKey||event.shiftKey)return;
    const item=current?.items.find(i=>i.id===link.dataset.newsId);if(item){event.preventDefault();window.TonkoReader.open(item);}
  });
  render();if(current)updateStatus(current);
  function syncReader(){
    const requested=new URLSearchParams(location.search).get('news');
    const item=current?.items.find(i=>i.id===requested);
    if(item)window.TonkoReader?.open(item,true);else window.TonkoReader?.close();
  }
  addEventListener('popstate',syncReader);syncReader();
  check();setInterval(check,60000);
})();
